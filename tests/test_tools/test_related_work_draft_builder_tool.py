"""Tests for the related_work_draft_builder tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.related_work_draft_builder_tool import (
    RELATED_WORK_DRAFT_KEYS,
    RelatedWorkDraftBuilder,
    RelatedWorkDraftBuilderInput,
)


def _matrix() -> dict[str, object]:
    return {
        "dimensions": ["method", "results", "limitations"],
        "rows": [
            {
                "paper_id": "P001",
                "title": "Paper One",
                "authors": ["Alice Example"],
                "source_path": "one.pdf",
                "cells": {
                    "method": {
                        "content": "Uses rule based extraction",
                        "evidence_ids": ["E001"],
                        "trace_status": "located",
                        "review_status": "pending_human_review",
                    },
                    "results": {
                        "content": "Links fields to source pages",
                        "evidence_ids": ["E002"],
                        "trace_status": "located",
                        "review_status": "pending_human_review",
                    },
                    "limitations": {
                        "content": "Does not guarantee semantics",
                        "evidence_ids": ["E003"],
                        "trace_status": "located",
                        "review_status": "pending_human_review",
                    },
                },
            },
            {
                "paper_id": "P002",
                "title": "Paper Two",
                "authors": ["Bob Researcher"],
                "source_path": "two.pdf",
                "cells": {
                    "method": {
                        "content": "Uses structured evidence tables",
                        "evidence_ids": ["E001"],
                        "trace_status": "located",
                        "review_status": "confirmed",
                    },
                    "results": {
                        "content": "This result was not located",
                        "evidence_ids": ["E002"],
                        "trace_status": "not_located",
                        "review_status": "pending_human_review",
                    },
                    "limitations": {
                        "content": "Requires human review",
                        "evidence_ids": ["E003"],
                        "trace_status": "located",
                        "review_status": "rejected",
                    },
                },
            },
        ],
        "comparison": {
            "paper_count": 2,
            "field_coverage": {
                "method": {"populated": 2, "located": 2, "unverified": 0, "missing": 0},
                "results": {"populated": 2, "located": 1, "unverified": 1, "missing": 0},
                "limitations": {
                    "populated": 2,
                    "located": 2,
                    "unverified": 0,
                    "missing": 0,
                },
            },
            "exact_matches": [],
            "evidence_gaps": [{"paper_id": "P002", "fields": ["results"]}],
        },
    }


@pytest.mark.asyncio
async def test_chinese_draft_uses_only_approved_located_evidence(tmp_path: Path) -> None:
    result = await RelatedWorkDraftBuilder().execute(
        RelatedWorkDraftBuilderInput(
            literature_matrix=_matrix(),
            approved_evidence_refs=["P001:E001", "P002:E001", "P001:E002"],
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    draft = json.loads(result.output)
    assert list(draft) == list(RELATED_WORK_DRAFT_KEYS)
    assert draft["title"] == "相关工作草稿"
    assert draft["language"] == "zh"
    assert draft["used_evidence"] == ["P001:E001", "P002:E001", "P001:E002"]
    assert "P002:E002" in draft["excluded_evidence"]
    assert draft["review_status"] == "draft_requires_final_review"

    paragraphs = [paragraph for section in draft["sections"] for paragraph in section["paragraphs"]]
    method = next(paragraph for paragraph in paragraphs if paragraph["dimension"] == "method")
    assert "Paper One" in method["text"]
    assert "Paper Two" in method["text"]
    assert method["citations"] == [
        {"paper_id": "P001", "title": "Paper One", "evidence_refs": ["P001:E001"]},
        {"paper_id": "P002", "title": "Paper Two", "evidence_refs": ["P002:E001"]},
    ]
    assert "This result was not located" not in result.output
    assert "Requires human review" not in result.output
    assert result.metadata["related_work_draft"] == draft


@pytest.mark.asyncio
async def test_english_draft_is_supported(tmp_path: Path) -> None:
    result = await RelatedWorkDraftBuilder().execute(
        RelatedWorkDraftBuilderInput(
            literature_matrix=_matrix(),
            approved_evidence_refs=["P001:E003"],
            language="en",
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    draft = json.loads(result.output)
    assert draft["title"] == "Related Work Draft"
    assert draft["language"] == "en"
    assert draft["sections"][0]["heading"] == "Limitations and Future Directions"
    assert "Paper One reports the following for limitations" in result.output


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("reference", "message"),
    [
        ("P999:E001", "Unknown evidence references"),
        ("P002:E002", "not source-located"),
        ("P002:E003", "Rejected evidence cannot be used"),
    ],
)
async def test_rejects_unknown_unlocated_or_rejected_evidence(
    tmp_path: Path,
    reference: str,
    message: str,
) -> None:
    result = await RelatedWorkDraftBuilder().execute(
        RelatedWorkDraftBuilderInput(
            literature_matrix=_matrix(),
            approved_evidence_refs=[reference],
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is True
    assert message in result.output


def test_requires_well_formed_unique_approvals() -> None:
    with pytest.raises(ValidationError, match="paper_id:evidence_id"):
        RelatedWorkDraftBuilderInput(
            literature_matrix=_matrix(),
            approved_evidence_refs=["E001"],
        )

    with pytest.raises(ValidationError, match="must be unique"):
        RelatedWorkDraftBuilderInput(
            literature_matrix=_matrix(),
            approved_evidence_refs=["P001:E001", "P001:E001"],
        )


def test_tool_is_registered_and_read_only() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("related_work_draft_builder")

    assert tool is not None
    arguments = RelatedWorkDraftBuilderInput(
        literature_matrix=_matrix(),
        approved_evidence_refs=["P001:E001"],
    )
    assert tool.is_read_only(arguments)
