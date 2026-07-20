"""Tests for the paper_card_extractor tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.paper_card_extractor_tool import (
    PAPER_CARD_KEYS,
    PaperCardExtractor,
    PaperCardExtractorInput,
    _build_paper_card,
)


def _write_minimal_pdf(path: Path, *, title: str = "", authors: str = "") -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    metadata: dict[str, str] = {}
    if title:
        metadata["/Title"] = title
    if authors:
        metadata["/Author"] = authors
    if metadata:
        writer.add_metadata(metadata)
    with path.open("wb") as handle:
        writer.write(handle)


@pytest.mark.asyncio
async def test_missing_path_returns_clear_error(tmp_path: Path) -> None:
    result = await PaperCardExtractor().execute(
        PaperCardExtractorInput(path="missing.pdf"),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is True
    assert "PDF file not found" in result.output


@pytest.mark.asyncio
async def test_non_pdf_returns_clear_error(tmp_path: Path) -> None:
    target = tmp_path / "paper.txt"
    target.write_text("not a pdf", encoding="utf-8")

    result = await PaperCardExtractor().execute(
        PaperCardExtractorInput(path="paper.txt"),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is True
    assert "not a PDF file" in result.output


@pytest.mark.asyncio
async def test_minimal_pdf_returns_strict_json_and_metadata(tmp_path: Path) -> None:
    pdf_path = tmp_path / "mock.pdf"
    _write_minimal_pdf(
        pdf_path,
        title="Mock ScholarPilot Paper",
        authors="Alice Example; Bob Researcher",
    )

    result = await PaperCardExtractor().execute(
        PaperCardExtractorInput(path="mock.pdf"),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    paper_card = json.loads(result.output)
    assert list(paper_card.keys()) == list(PAPER_CARD_KEYS)
    assert paper_card["title"] == "Mock ScholarPilot Paper"
    assert paper_card["authors"] == ["Alice Example", "Bob Researcher"]
    assert paper_card["abstract"] == ""
    assert paper_card["research_problem"] == ""
    assert paper_card["method"] == ""
    assert paper_card["dataset"] == ""
    assert paper_card["results"] == ""
    assert paper_card["limitations"] == ""
    assert paper_card["future_work"] == ""
    assert result.metadata["paper_card"] == paper_card
    assert result.metadata["source_path"] == "mock.pdf"
    assert result.metadata["page_count"] == 1


def test_section_heading_rules_extract_known_sections_without_fabricating() -> None:
    text = """
    ScholarPilot Paper
    Alice Example and Bob Researcher
    Abstract
    This paper studies traceable research-agent workflows.
    1 Introduction
    Researchers need paper reading workflows that preserve source context.
    2 Method
    We use conservative section-heading rules and local PDF parsing.
    3 Datasets
    The evaluation uses a mock PDF fixture.
    4 Results
    Results show that the tool returns a fixed JSON object.
    5 Limitations
    Rule-based extraction cannot guarantee semantic accuracy.
    6 Future Work
    Future versions should add evidence tables.
    """

    paper_card = _build_paper_card(text, {})

    assert paper_card["title"] == "ScholarPilot Paper"
    assert paper_card["authors"] == ["Alice Example", "Bob Researcher"]
    assert paper_card["abstract"] == "This paper studies traceable research-agent workflows."
    assert "preserve source context" in paper_card["research_problem"]
    assert "conservative section-heading rules" in paper_card["method"]
    assert "mock PDF fixture" in paper_card["dataset"]
    assert paper_card["results"] == "Results show that the tool returns a fixed JSON object."
    assert paper_card["limitations"] == "Rule-based extraction cannot guarantee semantic accuracy."
    assert paper_card["future_work"] == "Future versions should add evidence tables."


def test_missing_sections_remain_empty() -> None:
    paper_card = _build_paper_card("Only A Title\n", {})

    assert paper_card["title"] == "Only A Title"
    assert paper_card["authors"] == []
    for key in (
        "abstract",
        "research_problem",
        "method",
        "dataset",
        "results",
        "limitations",
        "future_work",
    ):
        assert paper_card[key] == ""


def test_tool_is_registered_and_read_only() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("paper_card_extractor")

    assert tool is not None
    assert tool.name == "paper_card_extractor"
    assert tool.input_model.__name__ == "PaperCardExtractorInput"
    assert tool.input_model.__module__ == "openharness.tools.paper_card_extractor_tool"
    assert tool.is_read_only(PaperCardExtractorInput(path="paper.pdf"))
