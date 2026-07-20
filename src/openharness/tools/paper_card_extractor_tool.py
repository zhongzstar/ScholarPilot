"""Extract a basic paper card from a local PDF."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


PAPER_CARD_KEYS = (
    "title",
    "authors",
    "abstract",
    "research_problem",
    "method",
    "dataset",
    "results",
    "limitations",
    "future_work",
)

_EMPTY_PAPER_CARD: dict[str, Any] = {
    "title": "",
    "authors": [],
    "abstract": "",
    "research_problem": "",
    "method": "",
    "dataset": "",
    "results": "",
    "limitations": "",
    "future_work": "",
}

_SECTION_ALIASES: dict[str, str] = {
    "abstract": "abstract",
    "summary": "abstract",
    "introduction": "introduction",
    "background": "background",
    "motivation": "motivation",
    "method": "method",
    "methods": "method",
    "methodology": "method",
    "approach": "method",
    "proposed method": "method",
    "model": "method",
    "dataset": "dataset",
    "datasets": "dataset",
    "data": "dataset",
    "data set": "dataset",
    "data sets": "dataset",
    "experimental setup": "dataset",
    "experiments": "results",
    "experiment": "results",
    "evaluation": "results",
    "results": "results",
    "experimental results": "results",
    "limitations": "limitations",
    "limitation": "limitations",
    "future work": "future_work",
    "future directions": "future_work",
    "conclusion and future work": "future_work",
}

_SECTION_OUTPUT_KEYS = {
    "abstract",
    "introduction",
    "background",
    "motivation",
    "method",
    "dataset",
    "results",
    "limitations",
    "future_work",
}

_MAX_FIELD_CHARS = 2500
_MAX_RESEARCH_PROBLEM_CHARS = 1200


class PaperCardExtractorInput(BaseModel):
    """Arguments for extracting a paper card from a PDF."""

    path: str = Field(description="Path to the local PDF file")


class PaperCardExtractor(BaseTool):
    """Extract a structured paper card from a local PDF."""

    name = "paper_card_extractor"
    description = (
        "Extract basic paper-card fields from a local PDF using metadata, page text, "
        "and conservative section-heading rules. Missing fields are returned empty."
    )
    input_model = PaperCardExtractorInput

    def is_read_only(self, arguments: PaperCardExtractorInput) -> bool:
        del arguments
        return True

    async def execute(
        self,
        arguments: PaperCardExtractorInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        path = _resolve_path(context.cwd, arguments.path)
        if not path.exists():
            return ToolResult(output=f"PDF file not found: {arguments.path}", is_error=True)
        if not path.is_file() or path.suffix.lower() != ".pdf":
            return ToolResult(output=f"Input is not a PDF file: {arguments.path}", is_error=True)

        try:
            pdf_text, metadata, page_count = _read_pdf(path)
        except Exception as exc:
            return ToolResult(output=f"Failed to read PDF: {exc}", is_error=True)

        paper_card = _build_paper_card(pdf_text, metadata)
        source_path = _display_path(path, context.cwd)
        return ToolResult(
            output=json.dumps(paper_card, ensure_ascii=False, indent=2),
            metadata={
                "paper_card": paper_card,
                "source_path": source_path,
                "page_count": page_count,
            },
        )


def _resolve_path(base: Path, candidate: str) -> Path:
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def _display_path(path: Path, cwd: Path) -> str:
    try:
        return str(path.relative_to(cwd.resolve()))
    except ValueError:
        return str(path)


def _read_pdf(path: Path) -> tuple[str, dict[str, str], int]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("pypdf is required to read PDF files") from exc

    reader = PdfReader(str(path))
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception as exc:
            raise RuntimeError("encrypted PDFs are not supported unless they can be opened without a password") from exc

    metadata = _normalize_metadata(getattr(reader, "metadata", None))
    pages = list(reader.pages)
    page_texts: list[str] = []
    for page in pages:
        try:
            page_texts.append(page.extract_text() or "")
        except Exception:
            page_texts.append("")
    return "\n".join(page_texts), metadata, len(pages)


def _normalize_metadata(raw_metadata: Any) -> dict[str, str]:
    metadata: dict[str, str] = {}
    if raw_metadata is None:
        return metadata

    for key in ("title", "author", "subject"):
        value = getattr(raw_metadata, key, None)
        if value:
            metadata[key] = str(value).strip()

    if hasattr(raw_metadata, "items"):
        for key, value in raw_metadata.items():
            if value is None:
                continue
            normalized_key = str(key).lstrip("/").lower()
            if normalized_key in {"title", "author", "subject"}:
                metadata.setdefault(normalized_key, str(value).strip())
    return {key: value for key, value in metadata.items() if value}


def _build_paper_card(pdf_text: str, metadata: dict[str, str]) -> dict[str, Any]:
    card = dict(_EMPTY_PAPER_CARD)
    lines = _clean_lines(pdf_text)
    first_page_lines = _first_page_lines(pdf_text)
    sections = _extract_sections(lines)

    card["title"] = _extract_title(metadata, first_page_lines)
    card["authors"] = _extract_authors(metadata, first_page_lines, card["title"])
    card["abstract"] = _limit_text(sections.get("abstract", ""), _MAX_FIELD_CHARS)
    card["research_problem"] = _limit_text(
        _first_available_section(sections, ("introduction", "background", "motivation")),
        _MAX_RESEARCH_PROBLEM_CHARS,
    )
    card["method"] = _limit_text(sections.get("method", ""), _MAX_FIELD_CHARS)
    card["dataset"] = _limit_text(sections.get("dataset", ""), _MAX_FIELD_CHARS)
    card["results"] = _limit_text(sections.get("results", ""), _MAX_FIELD_CHARS)
    card["limitations"] = _limit_text(sections.get("limitations", ""), _MAX_FIELD_CHARS)
    card["future_work"] = _limit_text(sections.get("future_work", ""), _MAX_FIELD_CHARS)

    return {key: card[key] for key in PAPER_CARD_KEYS}


def _clean_lines(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return [re.sub(r"\s+", " ", line).strip() for line in normalized.splitlines() if line.strip()]


def _first_page_lines(text: str) -> list[str]:
    first_page = text.split("\f", 1)[0]
    return _clean_lines(first_page)[:30]


def _extract_title(metadata: dict[str, str], first_page_lines: list[str]) -> str:
    title = metadata.get("title", "").strip()
    if title:
        return _compact_text(title)

    for line in first_page_lines:
        if _match_section_heading(line) is None and not _looks_like_affiliation(line):
            return _compact_text(line)
    return ""


def _extract_authors(
    metadata: dict[str, str],
    first_page_lines: list[str],
    title: str,
) -> list[str]:
    authors = _split_authors(metadata.get("author", ""))
    if authors:
        return authors

    title_seen = not title
    for line in first_page_lines:
        if title and _compact_text(line).lower() == title.lower():
            title_seen = True
            continue
        if not title_seen:
            continue
        if _match_section_heading(line) is not None:
            break
        if _looks_like_affiliation(line):
            continue
        authors = _split_authors(line)
        if authors and all(_looks_like_author_name(author) for author in authors):
            return authors
    return []


def _split_authors(raw: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", raw).strip()
    if not cleaned:
        return []
    if ";" in cleaned:
        parts = cleaned.split(";")
    elif re.search(r"\s+and\s+", cleaned, flags=re.IGNORECASE):
        parts = re.split(r"\s+and\s+", cleaned, flags=re.IGNORECASE)
    elif "," in cleaned and not re.search(r"\b[A-Z]\.\s*,", cleaned):
        parts = cleaned.split(",")
    else:
        parts = [cleaned]
    authors = [_clean_author(part) for part in parts]
    return [author for author in authors if author]


def _clean_author(value: str) -> str:
    value = re.sub(r"[\*\u2020\u2021\d]+", "", value)
    value = re.sub(r"\s+", " ", value).strip(" ,")
    return value


def _looks_like_author_name(value: str) -> bool:
    if not value or len(value) > 80:
        return False
    if any(char.isdigit() for char in value) or "@" in value or ":" in value:
        return False
    lowered = value.lower()
    if lowered in _SECTION_ALIASES or _looks_like_affiliation(value):
        return False
    tokens = [token.strip(".-") for token in value.split() if token.strip(".-")]
    if not 1 <= len(tokens) <= 6:
        return False
    return sum(1 for token in tokens if token[:1].isupper()) >= min(2, len(tokens))


def _looks_like_affiliation(value: str) -> bool:
    lowered = value.lower()
    markers = (
        "university",
        "institute",
        "department",
        "school of",
        "college",
        "laboratory",
        "lab ",
        "email",
        "http",
        "www.",
    )
    return any(marker in lowered for marker in markers)


def _extract_sections(lines: list[str]) -> dict[str, str]:
    hits: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        canonical = _match_section_heading(line)
        if canonical is not None:
            hits.append((index, canonical))

    sections = {key: "" for key in _SECTION_OUTPUT_KEYS}
    for hit_index, (line_index, section_key) in enumerate(hits):
        if section_key not in sections or sections[section_key]:
            continue
        start = line_index + 1
        end = hits[hit_index + 1][0] if hit_index + 1 < len(hits) else len(lines)
        content = _compact_text(" ".join(lines[start:end]))
        if content:
            sections[section_key] = content
    return sections


def _match_section_heading(line: str) -> str | None:
    if len(line) > 100:
        return None
    candidate = re.sub(r"^\s*(?:[IVXLCM]+\.|\d+(?:\.\d+)*\.?)\s+", "", line, flags=re.IGNORECASE)
    candidate = candidate.strip(" .:-\t").lower()
    candidate = re.sub(r"\s+", " ", candidate)
    if not candidate or len(candidate.split()) > 8:
        return None
    if candidate in _SECTION_ALIASES:
        return _SECTION_ALIASES[candidate]
    for alias, canonical in _SECTION_ALIASES.items():
        if candidate.startswith(alias + " "):
            return canonical
    return None


def _first_available_section(sections: dict[str, str], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = sections.get(key, "")
        if value:
            return value
    return ""


def _compact_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _limit_text(value: str, max_chars: int) -> str:
    text = _compact_text(value)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip()


__all__ = ["PaperCardExtractor", "PaperCardExtractorInput"]
