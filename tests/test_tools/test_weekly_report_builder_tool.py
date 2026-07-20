"""Tests for the weekly_report_builder tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from openharness.tools import create_default_tool_registry
from openharness.tools.base import ToolExecutionContext
from openharness.tools.weekly_report_builder_tool import (
    WEEKLY_REPORT_KEYS,
    WeeklyReportBuilder,
    WeeklyReportBuilderInput,
)


def _experiment_log(
    experiment_id: str = "EXP-20260713-ABCDEF01",
    *,
    date: str = "2026-07-13",
    status: str = "completed",
) -> dict[str, object]:
    return {
        "experiment_id": experiment_id,
        "date": date,
        "title": "Evidence tracing baseline",
        "hypothesis": "Structured evidence improves auditability",
        "environment": {"python": "3.11"},
        "parameters": {"papers": 3},
        "commands": ["python -m pytest tests/test_tools -q"],
        "result": "All tests passed" if status == "completed" else "",
        "interpretation": "The contract is stable" if status == "completed" else "",
        "failure_reason": "Waiting for data" if status in {"failed", "blocked"} else "",
        "next_actions": ["Add more fixtures"],
        "paper_refs": ["P001"],
        "evidence_refs": ["P001:E001"],
        "status": status,
        "review_status": "pending_human_review",
    }


@pytest.mark.asyncio
async def test_builds_chinese_weekly_report_json_and_markdown(tmp_path: Path) -> None:
    arguments = WeeklyReportBuilderInput(
        week_start="2026-07-13",
        week_end="2026-07-19",
        papers_read=[
            {
                "title": "Traceable Research Workflows",
                "authors": ["Alice Example"],
                "source_path": "papers/traceable.pdf",
                "insights": ["证据字段需要保留页码"],
                "evidence_refs": ["P001:E001"],
            }
        ],
        experiment_logs=[_experiment_log()],
        task_updates=[
            {"task": "完成 v0.6 工具设计", "status": "completed", "note": "已验证"},
            {"task": "准备演示", "status": "in_progress", "note": "待补示例"},
        ],
        blockers=["缺少公开演示论文"],
        decisions=["保持工具为只读 JSON 构建器"],
        next_week_plan=["补充端到端演示"],
    )

    result = await WeeklyReportBuilder().execute(
        arguments,
        ToolExecutionContext(cwd=tmp_path),
    )

    assert result.is_error is False
    report = json.loads(result.output)
    assert list(report) == list(WEEKLY_REPORT_KEYS)
    assert report["title"] == "ScholarPilot 科研周报"
    assert report["period"] == {"start": "2026-07-13", "end": "2026-07-19"}
    assert report["summary"] == {
        "papers_read": 1,
        "experiments_total": 1,
        "experiment_status_counts": {
            "planned": 0,
            "running": 0,
            "completed": 1,
            "failed": 0,
            "blocked": 0,
        },
        "tasks_completed": 1,
        "blocker_count": 1,
    }
    assert "# ScholarPilot 科研周报" in report["markdown"]
    assert "Traceable Research Workflows" in report["markdown"]
    assert "Evidence tracing baseline" in report["markdown"]
    assert "缺少公开演示论文" in report["markdown"]
    assert report["review_status"] == "pending_human_review"
    assert result.metadata["weekly_report"] == report


@pytest.mark.asyncio
async def test_english_empty_report_uses_explicit_empty_sections(tmp_path: Path) -> None:
    result = await WeeklyReportBuilder().execute(
        WeeklyReportBuilderInput(
            week_start="2026-07-13",
            week_end="2026-07-13",
            language="en",
        ),
        ToolExecutionContext(cwd=tmp_path),
    )

    report = json.loads(result.output)
    assert report["title"] == "ScholarPilot Weekly Report"
    assert report["summary"]["papers_read"] == 0
    assert report["summary"]["experiments_total"] == 0
    assert "No papers recorded" in report["markdown"]
    assert "No experiments recorded" in report["markdown"]
    assert "No blockers recorded" in report["markdown"]


def test_rejects_invalid_periods_and_out_of_period_experiments() -> None:
    with pytest.raises(ValidationError, match="must not be earlier"):
        WeeklyReportBuilderInput(week_start="2026-07-19", week_end="2026-07-13")

    with pytest.raises(ValidationError, match="at most 7"):
        WeeklyReportBuilderInput(week_start="2026-07-01", week_end="2026-07-19")

    with pytest.raises(ValidationError, match="outside the reporting period"):
        WeeklyReportBuilderInput(
            week_start="2026-07-13",
            week_end="2026-07-19",
            experiment_logs=[_experiment_log(date="2026-07-20")],
        )


def test_rejects_duplicate_experiment_ids_and_report_lists() -> None:
    log = _experiment_log()
    with pytest.raises(ValidationError, match="experiment_id values must be unique"):
        WeeklyReportBuilderInput(
            week_start="2026-07-13",
            week_end="2026-07-19",
            experiment_logs=[log, log],
        )

    with pytest.raises(ValidationError, match="list values must be unique"):
        WeeklyReportBuilderInput(
            week_start="2026-07-13",
            week_end="2026-07-19",
            blockers=["Waiting for data", "Waiting for data"],
        )


def test_rejects_internally_inconsistent_experiment_logs() -> None:
    log = _experiment_log(status="failed")
    log["failure_reason"] = ""

    with pytest.raises(ValidationError, match="require a failure_reason"):
        WeeklyReportBuilderInput(
            week_start="2026-07-13",
            week_end="2026-07-19",
            experiment_logs=[log],
        )


def test_tool_is_registered_and_read_only() -> None:
    registry = create_default_tool_registry()
    tool = registry.get("weekly_report_builder")

    assert tool is not None
    arguments = WeeklyReportBuilderInput(
        week_start="2026-07-13",
        week_end="2026-07-19",
    )
    assert tool.is_read_only(arguments)
