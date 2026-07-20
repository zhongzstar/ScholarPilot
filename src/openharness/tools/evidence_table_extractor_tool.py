"""Build a source-traceable evidence table from a paper PDF."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from openharness.tools.paper_card_extractor_tool import (
    _build_paper_card,
    _clean_lines,
    _compact_text,
    _display_path,
    _match_section_heading,
    _read_pdf_pages,
    _resolve_path,
)


EVIDENCE_FIELDS = (
    "abstract",
    "research_problem",
    "method",
    "dataset",
    "results",
    "limitations",
    "future_work",
)

EVIDENCE_TABLE_KEYS = (
    "paper",
    "source_path",
    "page_count",
    "rows",
    "missing_fields",
    "unverified_fields",
)

EVIDENCE_ROW_KEYS = (
    "evidence_id",
    "field",
    "content",
    "evidence_type",
    "page_number",
    "section",
    "source_quote",
    "confidence",
    "trace_status",
    "review_status",
)

_FIELD_SECTIONS: dict[str, tuple[str, ...]] = {
    "abstract": ("abstract",),
    "research_problem": ("introduction", "background", "motivation"),
    "method": ("method",),
    "dataset": ("dataset",),
    "results": ("results",),
    "limitations": ("limitations",),
    "future_work": ("future_work",),
}

_MAX_QUOTE_CHARS = 600
_ANCHOR_CHARS = 180


class PaperCardPayload(BaseModel):
    """Paper Card fields accepted from the v0.2 extractor."""

    model_config = ConfigDict(extra="forbid")

    title: str = ""
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    research_problem: str = ""
    method: str = ""
    dataset: str = ""
    results: str = ""
    limitations: str = ""
    future_work: str = ""


class EvidenceTableExtractorInput(BaseModel):
    """Arguments for tracing Paper Card fields to a local PDF."""

    path: str = Field(description="Path to the local PDF file")
    paper_card: PaperCardPayload | None = Field(
        default=None,
        description="Optional Paper Card returned by paper_card_extractor",
    )


class EvidenceTableExtractor(BaseTool):
    """Create evidence rows without adding claims that are absent from the PDF."""

    name = "evidence_table_extractor"
    description = (
        "Trace non-empty Paper Card fields back to page-level PDF text. Returns source "
        "quotes, confidence, trace status, and pending human-review status. It does not "
        "use an LLM or invent missing evidence."
    )
    input_model = EvidenceTableExtractorInput

    def is_read_only(self, arguments: EvidenceTableExtractorInput) -> bool:
        del arguments
        return True

    async def execute(
        self,
        arguments: EvidenceTableExtractorInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        path = _resolve_path(context.cwd, arguments.path)
        if not path.exists():
            return ToolResult(output=f"PDF file not found: {arguments.path}", is_error=True)
        if not path.is_file() or path.suffix.lower() != ".pdf":
            return ToolResult(output=f"Input is not a PDF file: {arguments.path}", is_error=True)

        try:
            page_texts, metadata = _read_pdf_pages(path)
        except Exception as exc:
            return ToolResult(output=f"Failed to read PDF: {exc}", is_error=True)

        if arguments.paper_card is None:
            paper_card = _build_paper_card("\f".join(page_texts), metadata)
        else:
            paper_card = arguments.paper_card.model_dump()

        source_path = _display_path(path, context.cwd)
        evidence_table = _build_evidence_table(
            paper_card=paper_card,
            page_texts=page_texts,
            source_path=source_path,
        )
        return ToolResult(
            output=json.dumps(evidence_table, ensure_ascii=False, indent=2),
            metadata={
                "evidence_table": evidence_table,
                "paper_card": paper_card,
                "source_path": source_path,
                "page_count": len(page_texts),
            },
        )


@dataclass(frozen=True)
class _SourceSegment:
    page_number: int
    section: str
    text: str


@dataclass(frozen=True)
class _TraceMatch:
    page_number: int
    section: str
    source_quote: str
    confidence: str


def _build_evidence_table(
    paper_card: dict[str, Any],
    page_texts: list[str],
    source_path: str,
) -> dict[str, Any]:
    segments = _build_source_segments(page_texts)
    rows: list[dict[str, Any]] = []
    missing_fields: list[str] = []
    unverified_fields: list[str] = []

    for field_name in EVIDENCE_FIELDS:
        content = _compact_text(str(paper_card.get(field_name, "") or ""))
        if not content:
            missing_fields.append(field_name)
            continue

        match = _locate_source(content, _FIELD_SECTIONS[field_name], segments)
        if match is None:
            unverified_fields.append(field_name)
            row = _unverified_row(len(rows) + 1, field_name, content)
        else:
            row = _matched_row(len(rows) + 1, field_name, content, match)
        rows.append(row)

    table = {
        "paper": {
            "title": _compact_text(str(paper_card.get("title", "") or "")),
            "authors": list(paper_card.get("authors", []) or []),
        },
        "source_path": source_path,
        "page_count": len(page_texts),
        "rows": rows,
        "missing_fields": missing_fields,
        "unverified_fields": unverified_fields,
    }
    return {key: table[key] for key in EVIDENCE_TABLE_KEYS}


def _build_source_segments(page_texts: list[str]) -> list[_SourceSegment]:
    segments: list[_SourceSegment] = []
    active_section = ""

    for page_number, page_text in enumerate(page_texts, start=1):
        section = active_section
        content_lines: list[str] = []

        def flush() -> None:
            if not section or not content_lines:
                return
            text = _compact_text(" ".join(content_lines))
            if text:
                segments.append(_SourceSegment(page_number, section, text))

        for line in _clean_lines(page_text):
            heading = _match_section_heading(line)
            if heading is None:
                if section:
                    content_lines.append(line)
                continue

            flush()
            content_lines = []
            section = heading
            active_section = heading

        flush()

    return segments


def _locate_source(
    content: str,
    expected_sections: tuple[str, ...],
    segments: list[_SourceSegment],
) -> _TraceMatch | None:
    candidates = [segment for segment in segments if segment.section in expected_sections]
    normalized_content = _compact_text(content)

    for segment in candidates:
        normalized_source = _compact_text(segment.text)
        start = normalized_source.casefold().find(normalized_content.casefold())
        if start >= 0:
            return _TraceMatch(
                page_number=segment.page_number,
                section=segment.section,
                source_quote=_quote_from(normalized_source, start),
                confidence="high",
            )

    anchor = normalized_content[:_ANCHOR_CHARS].rstrip()
    if len(anchor) < len(normalized_content):
        for segment in candidates:
            normalized_source = _compact_text(segment.text)
            start = normalized_source.casefold().find(anchor.casefold())
            if start >= 0:
                return _TraceMatch(
                    page_number=segment.page_number,
                    section=segment.section,
                    source_quote=_quote_from(normalized_source, start),
                    confidence="medium",
                )

    return None


def _quote_from(source: str, start: int) -> str:
    quote_start = max(0, start - 80)
    quote_end = min(len(source), quote_start + _MAX_QUOTE_CHARS)
    quote = source[quote_start:quote_end].strip()
    if quote_start > 0:
        quote = "..." + quote
    if quote_end < len(source):
        quote += "..."
    return quote


def _matched_row(
    index: int,
    field_name: str,
    content: str,
    match: _TraceMatch,
) -> dict[str, Any]:
    row = {
        "evidence_id": f"E{index:03d}",
        "field": field_name,
        "content": content,
        "evidence_type": "direct_source_text",
        "page_number": match.page_number,
        "section": match.section,
        "source_quote": match.source_quote,
        "confidence": match.confidence,
        "trace_status": "located",
        "review_status": "pending_human_review",
    }
    return {key: row[key] for key in EVIDENCE_ROW_KEYS}


def _unverified_row(index: int, field_name: str, content: str) -> dict[str, Any]:
    row = {
        "evidence_id": f"E{index:03d}",
        "field": field_name,
        "content": content,
        "evidence_type": "unverified",
        "page_number": None,
        "section": "",
        "source_quote": "",
        "confidence": "none",
        "trace_status": "not_located",
        "review_status": "pending_human_review",
    }
    return {key: row[key] for key in EVIDENCE_ROW_KEYS}


__all__ = [
    "EvidenceTableExtractor",
    "EvidenceTableExtractorInput",
    "PaperCardPayload",
]
