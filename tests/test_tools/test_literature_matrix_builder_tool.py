"""Tests for the literature_matrix_builder tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.literature_matrix_builder_tool import (
    LITERATURE_MATRIX_KEYS,
    MATRIX_CELL_KEYS,
    MATRIX_ROW_KEYS,
    LiteratureMatrixBuilder,
    LiteratureMatrixBuilderInput,
)


def _evidence_table(
    title: str,
    source_path: str,
    values: dict[str, str],
    *,
    unverified: set[str] | None = None,
) -> dict[str, object]:
    unverified = unverified or set()
    rows: list[dict[str, object]] = []
    all_fields = (
        "abstract",
        "research_problem",
        "method",
        "dataset",
        "results",
        "limitations",
        "future_work",
    )
    for index, (field, content) in enumerate(values.items(), start=1):
        located = field not in unverified
        rows.append(
            {
                "evidence_id": f"E{index:03d}",
                "field": field,
                "content": content,
                "evidence_type": "direct_source_text" if located else "unverified",
                "page_number": index if located else None,
                "section": field if located else "",
                "source_quote": content if located else "",
                "confidence": "high" if located else "none",
                "trace_status": "located" if located else "not_located",
                "review_status": "pending_human_review",
            }
        )
    return {
        "paper": {"title": title, "authors": [f"Author of {title}"]},
        "source_path": source_path,
        "page_count": 6,
        "rows": rows,
        "missing_fields": [field for field in all_fields if field not in values],
        "unverified_fields": list(unverified),
    }


@pytest.mark.asyncio
async def test_builds_matrix_with_coverage_exact_matches_and_gaps(tmp_path: Path) -> None:
    first = _evidence_table(
        "Paper One",
        "papers/one.pdf",
        {
            "research_problem": "Traceable research workflows",
            "method": "Rule based extraction",
            "dataset": "Synthetic PDF fixtures",
            "results": "Fields are linked to evidence",
            "limitations": "Semantic accuracy is not guaranteed",
        },
    )
    second = _evidence_table(
        "Paper Two",
        "papers/two.pdf",
        {
            "research_problem": "Auditable literature reviews",
            "method": "  rule BASED   extraction ",
            "results": "Evidence gaps remain visible",
            "limitations": "Human review is required",
        },
    )

    result = await LiteratureMatrixBuilder().execute(
        LiteratureMatrixBuilderInput(evidence_tables=[first, second]),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    matrix = json.loads(result.output)
    assert list(matrix) == list(LITERATURE_MATRIX_KEYS)
    assert matrix["dimensions"] == [
        "research_problem",
        "method",
        "dataset",
        "results",
        "limitations",
        "future_work",
    ]
    assert len(matrix["rows"]) == 2
    assert all(list(row) == list(MATRIX_ROW_KEYS) for row in matrix["rows"])
    assert all(
        list(cell) == list(MATRIX_CELL_KEYS)
        for row in matrix["rows"]
        for cell in row["cells"].values()
    )
    assert matrix["rows"][0]["paper_id"] == "P001"
    assert matrix["rows"][1]["paper_id"] == "P002"
    assert matrix["rows"][1]["cells"]["dataset"]["trace_status"] == "missing"

    comparison = matrix["comparison"]
    assert comparison["paper_count"] == 2
    assert comparison["field_coverage"]["dataset"] == {
        "populated": 1,
        "located": 1,
        "unverified": 0,
        "missing": 1,
    }
    assert comparison["exact_matches"] == [
        {
            "dimension": "method",
            "content": "Rule based extraction",
            "paper_ids": ["P001", "P002"],
        }
    ]
    gaps = {gap["paper_id"]: gap["fields"] for gap in comparison["evidence_gaps"]}
    assert gaps["P001"] == ["future_work"]
    assert gaps["P002"] == ["dataset", "future_work"]
    assert result.metadata["literature_matrix"] == matrix
    assert result.metadata["paper_count"] == 2


@pytest.mark.asyncio
async def test_selected_dimensions_preserve_order_and_unverified_cells_are_gaps(
    tmp_path: Path,
) -> None:
    first = _evidence_table(
        "Paper One",
        "one.pdf",
        {"method": "Method A", "results": "Result A"},
    )
    second = _evidence_table(
        "Paper Two",
        "two.pdf",
        {"method": "Method A", "results": "Unsupported result"},
        unverified={"results"},
    )

    result = await LiteratureMatrixBuilder().execute(
        LiteratureMatrixBuilderInput(
            evidence_tables=[first, second],
            dimensions=["results", "method"],
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    matrix = json.loads(result.output)
    assert matrix["dimensions"] == ["results", "method"]
    assert list(matrix["rows"][0]["cells"]) == ["results", "method"]
    assert matrix["comparison"]["field_coverage"]["results"]["unverified"] == 1
    assert matrix["comparison"]["exact_matches"] == [
        {
            "dimension": "method",
            "content": "Method A",
            "paper_ids": ["P001", "P002"],
        }
    ]
    assert matrix["comparison"]["evidence_gaps"] == [{"paper_id": "P002", "fields": ["results"]}]


def test_requires_two_tables_and_unique_dimensions() -> None:
    table = _evidence_table("Paper One", "one.pdf", {"method": "Method A"})

    with pytest.raises(ValidationError, match="at least 2"):
        LiteratureMatrixBuilderInput(evidence_tables=[table])

    with pytest.raises(ValidationError, match="must be unique"):
        LiteratureMatrixBuilderInput(
            evidence_tables=[table, table],
            dimensions=["method", "method"],
        )


def test_rejects_duplicate_evidence_fields() -> None:
    table = _evidence_table("Paper One", "one.pdf", {"method": "Method A"})
    duplicate = dict(table["rows"][0])
    duplicate["evidence_id"] = "E999"
    table["rows"] = [*table["rows"], duplicate]

    with pytest.raises(ValidationError, match="fields must be unique"):
        LiteratureMatrixBuilderInput(evidence_tables=[table, table])


def test_tool_is_registered_and_read_only() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("literature_matrix_builder")
    table = _evidence_table("Paper One", "one.pdf", {"method": "Method A"})

    assert tool is not None
    arguments = LiteratureMatrixBuilderInput(evidence_tables=[table, table])
    assert tool.is_read_only(arguments)
