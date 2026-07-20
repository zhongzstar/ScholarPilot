"""Tests for the evidence_table_extractor tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.evidence_table_extractor_tool import (
    EVIDENCE_ROW_KEYS,
    EVIDENCE_TABLE_KEYS,
    EvidenceTableExtractor,
    EvidenceTableExtractorInput,
    PaperCardPayload,
)


def _write_text_pdf(
    path: Path,
    pages: list[list[str]],
    *,
    title: str = "Traceable Research Workflows",
    authors: str = "Alice Example; Bob Researcher",
) -> None:
    writer = PdfWriter()
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
            NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
        }
    )
    font_reference = writer._add_object(font)

    for lines in pages:
        page = writer.add_blank_page(width=612, height=792)
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_reference})}
        )
        commands = ["BT", "/F1 11 Tf", "72 740 Td", "16 TL"]
        for line in lines:
            escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
            commands.extend((f"({escaped}) Tj", "T*"))
        commands.append("ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(commands).encode("latin-1"))
        page[NameObject("/Contents")] = writer._add_object(stream)

    writer.add_metadata({"/Title": title, "/Author": authors})
    with path.open("wb") as handle:
        writer.write(handle)


def _paper_pages() -> list[list[str]]:
    return [
        [
            "Traceable Research Workflows",
            "Alice Example and Bob Researcher",
            "Abstract",
            "This paper studies traceable research assistant workflows.",
            "1 Introduction",
            "Researchers need paper notes that preserve source context.",
            "2 Method",
            "We use local PDF parsing and conservative heading rules.",
        ],
        [
            "3 Dataset",
            "The evaluation uses a synthetic PDF fixture.",
            "4 Results",
            "The extractor links every populated field to source text.",
            "5 Limitations",
            "Rule based extraction cannot guarantee semantic accuracy.",
            "6 Future Work",
            "Future versions should compare evidence across papers.",
        ],
    ]


@pytest.mark.asyncio
async def test_missing_path_returns_clear_error(tmp_path: Path) -> None:
    result = await EvidenceTableExtractor().execute(
        EvidenceTableExtractorInput(path="missing.pdf"),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is True
    assert "PDF file not found" in result.output


@pytest.mark.asyncio
async def test_non_pdf_returns_clear_error(tmp_path: Path) -> None:
    target = tmp_path / "paper.txt"
    target.write_text("not a pdf", encoding="utf-8")

    result = await EvidenceTableExtractor().execute(
        EvidenceTableExtractorInput(path="paper.txt"),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is True
    assert "not a PDF file" in result.output


@pytest.mark.asyncio
async def test_builds_source_traced_rows_from_dynamic_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mock.pdf"
    _write_text_pdf(pdf_path, _paper_pages())

    result = await EvidenceTableExtractor().execute(
        EvidenceTableExtractorInput(path="mock.pdf"),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    evidence_table = json.loads(result.output)
    assert list(evidence_table) == list(EVIDENCE_TABLE_KEYS)
    assert evidence_table["paper"] == {
        "title": "Traceable Research Workflows",
        "authors": ["Alice Example", "Bob Researcher"],
    }
    assert evidence_table["source_path"] == "mock.pdf"
    assert evidence_table["page_count"] == 2
    assert evidence_table["missing_fields"] == []
    assert evidence_table["unverified_fields"] == []

    rows = {row["field"]: row for row in evidence_table["rows"]}
    assert set(rows) == {
        "abstract",
        "research_problem",
        "method",
        "dataset",
        "results",
        "limitations",
        "future_work",
    }
    assert all(list(row) == list(EVIDENCE_ROW_KEYS) for row in rows.values())
    assert rows["abstract"]["page_number"] == 1
    assert rows["abstract"]["section"] == "abstract"
    assert rows["dataset"]["page_number"] == 2
    assert rows["future_work"]["section"] == "future_work"
    assert all(row["trace_status"] == "located" for row in rows.values())
    assert all(row["review_status"] == "pending_human_review" for row in rows.values())
    assert all(len(row["source_quote"]) <= 603 for row in rows.values())
    assert result.metadata["evidence_table"] == evidence_table
    assert result.metadata["source_path"] == "mock.pdf"
    assert result.metadata["page_count"] == 2


@pytest.mark.asyncio
async def test_unmatched_card_content_is_flagged_without_fabricated_source(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mock.pdf"
    _write_text_pdf(pdf_path, _paper_pages())
    paper_card = PaperCardPayload(
        title="Traceable Research Workflows",
        authors=["Alice Example", "Bob Researcher"],
        method="This method is not present in the PDF.",
    )

    result = await EvidenceTableExtractor().execute(
        EvidenceTableExtractorInput(path="mock.pdf", paper_card=paper_card),
        ToolExecutionContext(cwd=tmp_path),
    )

    evidence_table = json.loads(result.output)
    assert evidence_table["unverified_fields"] == ["method"]
    assert set(evidence_table["missing_fields"]) == {
        "abstract",
        "research_problem",
        "dataset",
        "results",
        "limitations",
        "future_work",
    }
    row = evidence_table["rows"][0]
    assert row["field"] == "method"
    assert row["evidence_type"] == "unverified"
    assert row["page_number"] is None
    assert row["section"] == ""
    assert row["source_quote"] == ""
    assert row["confidence"] == "none"
    assert row["trace_status"] == "not_located"
    assert row["review_status"] == "pending_human_review"


def test_tool_is_registered_and_read_only() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("evidence_table_extractor")

    assert tool is not None
    assert tool.name == "evidence_table_extractor"
    arguments = EvidenceTableExtractorInput(path="paper.pdf")
    assert tool.is_read_only(arguments)
