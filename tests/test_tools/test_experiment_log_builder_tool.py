"""Tests for the experiment_log_builder tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.experiment_log_builder_tool import (
    EXPERIMENT_LOG_KEYS,
    ExperimentLogBuilder,
    ExperimentLogBuilderInput,
)


def _completed_input() -> ExperimentLogBuilderInput:
    return ExperimentLogBuilderInput(
        date="2026-07-13",
        title="  Evidence tracing baseline  ",
        hypothesis="Page-level evidence links improve auditability.",
        environment={"python": "3.11", "device": "CPU"},
        parameters={"papers": 3, "threshold": 0.8, "dry_run": True},
        commands=["python -m pytest tests/test_tools -q"],
        result="All focused tests passed.",
        interpretation="The structured tool contract is stable.",
        next_actions=["Run the full tool suite"],
        paper_refs=["P001"],
        evidence_refs=["P001:E001"],
        status="completed",
    )


@pytest.mark.asyncio
async def test_builds_strict_deterministic_experiment_log(tmp_path: Path) -> None:
    tool = ExperimentLogBuilder()
    arguments = _completed_input()

    first = await tool.execute(arguments, ToolExecutionContext(cwd=tmp_path))
    second = await tool.execute(arguments, ToolExecutionContext(cwd=tmp_path))

    assert first.is_error is False
    assert first.output == second.output
    log = json.loads(first.output)
    assert list(log) == list(EXPERIMENT_LOG_KEYS)
    assert log["experiment_id"].startswith("EXP-20260713-")
    assert log["title"] == "Evidence tracing baseline"
    assert log["date"] == "2026-07-13"
    assert log["parameters"] == {"papers": 3, "threshold": 0.8, "dry_run": True}
    assert log["paper_refs"] == ["P001"]
    assert log["evidence_refs"] == ["P001:E001"]
    assert log["review_status"] == "pending_human_review"
    assert first.metadata["experiment_log"] == log
    assert first.metadata["experiment_id"] == log["experiment_id"]


@pytest.mark.asyncio
async def test_preserves_valid_custom_experiment_id(tmp_path: Path) -> None:
    data = _completed_input().model_dump()
    data["experiment_id"] = "EXP-custom_01"
    arguments = ExperimentLogBuilderInput(**data)

    result = await ExperimentLogBuilder().execute(
        arguments,
        ToolExecutionContext(cwd=tmp_path),
    )

    assert json.loads(result.output)["experiment_id"] == "EXP-custom_01"


def test_status_validation_requires_real_user_supplied_details() -> None:
    base = {
        "date": "2026-07-13",
        "title": "Baseline",
        "hypothesis": "A testable hypothesis",
    }

    with pytest.raises(ValidationError, match="require a result or interpretation"):
        ExperimentLogBuilderInput(**base, status="completed")

    with pytest.raises(ValidationError, match="require a failure_reason"):
        ExperimentLogBuilderInput(**base, status="failed")

    with pytest.raises(ValidationError, match="require a failure_reason"):
        ExperimentLogBuilderInput(**base, status="blocked")


def test_rejects_invalid_ids_and_duplicate_references() -> None:
    data = _completed_input().model_dump()
    data["experiment_id"] = "bad id"
    with pytest.raises(ValidationError, match="may contain only"):
        ExperimentLogBuilderInput(**data)

    data = _completed_input().model_dump()
    data["evidence_refs"] = ["P001:E001", "P001:E001"]
    with pytest.raises(ValidationError, match="must be unique"):
        ExperimentLogBuilderInput(**data)


def test_tool_is_registered_and_read_only() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("experiment_log_builder")

    assert tool is not None
    assert tool.is_read_only(_completed_input())
