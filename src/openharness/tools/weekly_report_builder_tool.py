"""Aggregate research artifacts into a deterministic Weekly Report."""

from __future__ import annotations

from datetime import date
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from openharness.tools.experiment_log_builder_tool import (
    ExperimentLogPayload,
    ExperimentStatus,
)


ReportLanguage = Literal["zh", "en"]
TaskStatus = Literal["planned", "in_progress", "completed", "blocked"]

WEEKLY_REPORT_KEYS = (
    "title",
    "period",
    "summary",
    "papers_read",
    "experiments",
    "task_updates",
    "blockers",
    "decisions",
    "next_week_plan",
    "markdown",
    "review_status",
)

_EXPERIMENT_STATUSES: tuple[ExperimentStatus, ...] = (
    "planned",
    "running",
    "completed",
    "failed",
    "blocked",
)


class PaperReadingPayload(BaseModel):
    """One paper-reading entry included in a weekly report."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)
    source_path: str = ""
    insights: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("Paper title must not be blank")
        return cleaned

    @field_validator("authors", "insights", "evidence_refs")
    @classmethod
    def validate_unique_lists(cls, value: list[str]) -> list[str]:
        cleaned = [_clean_text(item) for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Paper-reading list values must not be blank")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Paper-reading list values must be unique")
        return cleaned


class TaskUpdatePayload(BaseModel):
    """Auditable task status supplied to the weekly report."""

    model_config = ConfigDict(extra="forbid")

    task: str = Field(min_length=1)
    status: TaskStatus
    note: str = ""

    @field_validator("task", "note")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _clean_text(value)


class ReportPeriodPayload(BaseModel):
    """Inclusive weekly reporting period."""

    model_config = ConfigDict(extra="forbid")

    start: date
    end: date


class WeeklySummaryPayload(BaseModel):
    """Mechanical counts computed from report inputs."""

    model_config = ConfigDict(extra="forbid")

    papers_read: int = Field(ge=0)
    experiments_total: int = Field(ge=0)
    experiment_status_counts: dict[ExperimentStatus, int]
    tasks_completed: int = Field(ge=0)
    blocker_count: int = Field(ge=0)


class WeeklyReportPayload(BaseModel):
    """Reusable v0.6 Weekly Report JSON and Markdown artifact."""

    model_config = ConfigDict(extra="forbid")

    title: str
    period: ReportPeriodPayload
    summary: WeeklySummaryPayload
    papers_read: list[PaperReadingPayload]
    experiments: list[ExperimentLogPayload]
    task_updates: list[TaskUpdatePayload]
    blockers: list[str]
    decisions: list[str]
    next_week_plan: list[str]
    markdown: str
    review_status: Literal["pending_human_review"]


class WeeklyReportBuilderInput(BaseModel):
    """Research records to aggregate into one weekly report."""

    model_config = ConfigDict(extra="forbid")

    week_start: date
    week_end: date
    papers_read: list[PaperReadingPayload] = Field(default_factory=list)
    experiment_logs: list[ExperimentLogPayload] = Field(default_factory=list)
    task_updates: list[TaskUpdatePayload] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    next_week_plan: list[str] = Field(default_factory=list)
    language: ReportLanguage = "zh"

    @field_validator("blockers", "decisions", "next_week_plan")
    @classmethod
    def validate_unique_text_lists(cls, value: list[str]) -> list[str]:
        cleaned = [_clean_text(item) for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Weekly Report list values must not be blank")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Weekly Report list values must be unique")
        return cleaned

    @model_validator(mode="after")
    def validate_period_and_logs(self) -> WeeklyReportBuilderInput:
        day_count = (self.week_end - self.week_start).days
        if day_count < 0:
            raise ValueError("week_end must not be earlier than week_start")
        if day_count > 6:
            raise ValueError("Weekly Report periods may cover at most 7 inclusive days")
        experiment_ids = [log.experiment_id for log in self.experiment_logs]
        if len(experiment_ids) != len(set(experiment_ids)):
            raise ValueError("Weekly Report experiment_id values must be unique")
        outside_period = [
            log.experiment_id
            for log in self.experiment_logs
            if not self.week_start <= log.date <= self.week_end
        ]
        if outside_period:
            raise ValueError(
                "Experiment logs outside the reporting period: " + ", ".join(outside_period)
            )
        return self


class WeeklyReportBuilder(BaseTool):
    """Aggregate supplied records without inventing progress or conclusions."""

    name = "weekly_report_builder"
    description = (
        "Build a Chinese or English Weekly Report from paper-reading entries, Experiment "
        "Logs, task updates, blockers, decisions, and next-week plans. Returns strict JSON "
        "plus deterministic Markdown without using an LLM."
    )
    input_model = WeeklyReportBuilderInput

    def is_read_only(self, arguments: WeeklyReportBuilderInput) -> bool:
        del arguments
        return True

    async def execute(
        self,
        arguments: WeeklyReportBuilderInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del context
        report = _build_weekly_report(arguments)
        payload = report.model_dump(mode="json")
        return ToolResult(
            output=json.dumps(payload, ensure_ascii=False, indent=2),
            metadata={
                "weekly_report": payload,
                "period": payload["period"],
                "summary": payload["summary"],
            },
        )


def _build_weekly_report(arguments: WeeklyReportBuilderInput) -> WeeklyReportPayload:
    status_counts: dict[ExperimentStatus, int] = {
        status: sum(log.status == status for log in arguments.experiment_logs)
        for status in _EXPERIMENT_STATUSES
    }
    summary = WeeklySummaryPayload(
        papers_read=len(arguments.papers_read),
        experiments_total=len(arguments.experiment_logs),
        experiment_status_counts=status_counts,
        tasks_completed=sum(update.status == "completed" for update in arguments.task_updates),
        blocker_count=len(arguments.blockers),
    )
    period = ReportPeriodPayload(start=arguments.week_start, end=arguments.week_end)
    title = "ScholarPilot 科研周报" if arguments.language == "zh" else "ScholarPilot Weekly Report"
    markdown = _build_markdown(arguments, title, summary)
    return WeeklyReportPayload(
        title=title,
        period=period,
        summary=summary,
        papers_read=arguments.papers_read,
        experiments=arguments.experiment_logs,
        task_updates=arguments.task_updates,
        blockers=arguments.blockers,
        decisions=arguments.decisions,
        next_week_plan=arguments.next_week_plan,
        markdown=markdown,
        review_status="pending_human_review",
    )


def _build_markdown(
    arguments: WeeklyReportBuilderInput,
    title: str,
    summary: WeeklySummaryPayload,
) -> str:
    if arguments.language == "zh":
        return _build_zh_markdown(arguments, title, summary)
    return _build_en_markdown(arguments, title, summary)


def _build_zh_markdown(
    arguments: WeeklyReportBuilderInput,
    title: str,
    summary: WeeklySummaryPayload,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"报告周期：{arguments.week_start.isoformat()} 至 {arguments.week_end.isoformat()}",
        "",
        "## 本周概览",
        "",
        f"- 阅读论文：{summary.papers_read} 篇",
        f"- 实验记录：{summary.experiments_total} 条",
        f"- 已完成任务：{summary.tasks_completed} 项",
        f"- 当前阻塞：{summary.blocker_count} 项",
        "",
        "## 论文阅读",
        "",
    ]
    lines.extend(_paper_lines(arguments.papers_read, "zh"))
    lines.extend(["", "## 实验进展", ""])
    lines.extend(_experiment_lines(arguments.experiment_logs, "zh"))
    lines.extend(["", "## 任务更新", ""])
    lines.extend(_task_lines(arguments.task_updates, "zh"))
    lines.extend(["", "## 阻塞", ""])
    lines.extend(_plain_lines(arguments.blockers, "暂无阻塞"))
    lines.extend(["", "## 本周决策", ""])
    lines.extend(_plain_lines(arguments.decisions, "暂无决策记录"))
    lines.extend(["", "## 下周计划", ""])
    lines.extend(_plain_lines(arguments.next_week_plan, "暂无计划记录"))
    return "\n".join(lines).strip() + "\n"


def _build_en_markdown(
    arguments: WeeklyReportBuilderInput,
    title: str,
    summary: WeeklySummaryPayload,
) -> str:
    lines = [
        f"# {title}",
        "",
        f"Period: {arguments.week_start.isoformat()} to {arguments.week_end.isoformat()}",
        "",
        "## Summary",
        "",
        f"- Papers read: {summary.papers_read}",
        f"- Experiment logs: {summary.experiments_total}",
        f"- Tasks completed: {summary.tasks_completed}",
        f"- Blockers: {summary.blocker_count}",
        "",
        "## Papers Read",
        "",
    ]
    lines.extend(_paper_lines(arguments.papers_read, "en"))
    lines.extend(["", "## Experiments", ""])
    lines.extend(_experiment_lines(arguments.experiment_logs, "en"))
    lines.extend(["", "## Task Updates", ""])
    lines.extend(_task_lines(arguments.task_updates, "en"))
    lines.extend(["", "## Blockers", ""])
    lines.extend(_plain_lines(arguments.blockers, "No blockers recorded"))
    lines.extend(["", "## Decisions", ""])
    lines.extend(_plain_lines(arguments.decisions, "No decisions recorded"))
    lines.extend(["", "## Next Week", ""])
    lines.extend(_plain_lines(arguments.next_week_plan, "No plans recorded"))
    return "\n".join(lines).strip() + "\n"


def _paper_lines(papers: list[PaperReadingPayload], language: ReportLanguage) -> list[str]:
    if not papers:
        return ["- 暂无论文阅读记录" if language == "zh" else "- No papers recorded"]
    lines: list[str] = []
    for paper in papers:
        authors = ", ".join(paper.authors)
        author_suffix = f"（{authors}）" if language == "zh" and authors else ""
        if language == "en" and authors:
            author_suffix = f" ({authors})"
        insights = "；".join(paper.insights) if language == "zh" else "; ".join(paper.insights)
        insight_suffix = f"：{insights}" if language == "zh" and insights else ""
        if language == "en" and insights:
            insight_suffix = f": {insights}"
        lines.append(f"- **{paper.title}**{author_suffix}{insight_suffix}")
    return lines


def _experiment_lines(
    experiments: list[ExperimentLogPayload],
    language: ReportLanguage,
) -> list[str]:
    if not experiments:
        return ["- 暂无实验记录" if language == "zh" else "- No experiments recorded"]
    lines: list[str] = []
    for log in experiments:
        if language == "zh":
            lines.extend(
                [
                    f"### {log.experiment_id}：{log.title}",
                    "",
                    f"- 状态：{log.status}",
                    f"- 假设：{log.hypothesis}",
                    f"- 结果：{log.result or '暂无'}",
                    f"- 解释：{log.interpretation or '暂无'}",
                    f"- 失败或阻塞原因：{log.failure_reason or '暂无'}",
                    f"- 下一步：{'；'.join(log.next_actions) if log.next_actions else '暂无'}",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    f"### {log.experiment_id}: {log.title}",
                    "",
                    f"- Status: {log.status}",
                    f"- Hypothesis: {log.hypothesis}",
                    f"- Result: {log.result or 'None recorded'}",
                    f"- Interpretation: {log.interpretation or 'None recorded'}",
                    f"- Failure or blocker: {log.failure_reason or 'None recorded'}",
                    f"- Next actions: {'; '.join(log.next_actions) if log.next_actions else 'None'}",
                    "",
                ]
            )
    if lines and not lines[-1]:
        lines.pop()
    return lines


def _task_lines(tasks: list[TaskUpdatePayload], language: ReportLanguage) -> list[str]:
    if not tasks:
        return ["- 暂无任务更新" if language == "zh" else "- No task updates recorded"]
    lines = []
    for task in tasks:
        separator = "：" if language == "zh" else ": "
        note = f"{separator}{task.note}" if task.note else ""
        lines.append(f"- [{task.status}] {task.task}{note}")
    return lines


def _plain_lines(values: list[str], empty_message: str) -> list[str]:
    return [f"- {value}" for value in values] if values else [f"- {empty_message}"]


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


__all__ = [
    "PaperReadingPayload",
    "TaskUpdatePayload",
    "WeeklyReportBuilder",
    "WeeklyReportBuilderInput",
    "WeeklyReportPayload",
]
