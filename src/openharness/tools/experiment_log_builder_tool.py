"""Build a deterministic, structured Experiment Log artifact."""

from __future__ import annotations

from datetime import date
import hashlib
import json
import re
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


ExperimentStatus = Literal["planned", "running", "completed", "failed", "blocked"]

EXPERIMENT_LOG_KEYS = (
    "experiment_id",
    "date",
    "title",
    "hypothesis",
    "environment",
    "parameters",
    "commands",
    "result",
    "interpretation",
    "failure_reason",
    "next_actions",
    "paper_refs",
    "evidence_refs",
    "status",
    "review_status",
)


class ExperimentLogBuilderInput(BaseModel):
    """Structured experiment information supplied by the researcher or agent."""

    model_config = ConfigDict(extra="forbid")

    experiment_id: str | None = None
    date: date
    title: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    environment: dict[str, str] = Field(default_factory=dict)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    commands: list[str] = Field(default_factory=list)
    result: str = ""
    interpretation: str = ""
    failure_reason: str = ""
    next_actions: list[str] = Field(default_factory=list)
    paper_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    status: ExperimentStatus

    @field_validator("experiment_id")
    @classmethod
    def validate_experiment_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned or re.fullmatch(r"[A-Za-z0-9._-]+", cleaned) is None:
            raise ValueError("experiment_id may contain only letters, numbers, '.', '_', and '-'")
        return cleaned

    @field_validator("title", "hypothesis")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if not cleaned:
            raise ValueError("Required experiment text must not be blank")
        return cleaned

    @field_validator("next_actions", "paper_refs", "evidence_refs")
    @classmethod
    def validate_unique_lists(cls, value: list[str]) -> list[str]:
        cleaned = [_clean_text(item) for item in value]
        if any(not item for item in cleaned):
            raise ValueError("Experiment list values must not be blank")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Experiment list values must be unique")
        return cleaned

    @field_validator("commands")
    @classmethod
    def validate_commands(cls, value: list[str]) -> list[str]:
        cleaned = [command.strip() for command in value]
        if any(not command for command in cleaned):
            raise ValueError("Experiment commands must not be blank")
        return cleaned

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned = {_clean_text(key): _clean_text(item) for key, item in value.items()}
        if any(not key or not item for key, item in cleaned.items()):
            raise ValueError("Experiment environment keys and values must not be blank")
        if len(cleaned) != len(value):
            raise ValueError("Experiment environment keys must be unique after normalization")
        return cleaned

    @model_validator(mode="after")
    def validate_status_details(self) -> ExperimentLogBuilderInput:
        if self.status == "completed" and not (self.result.strip() or self.interpretation.strip()):
            raise ValueError("Completed experiments require a result or interpretation")
        if self.status in {"failed", "blocked"} and not self.failure_reason.strip():
            raise ValueError("Failed or blocked experiments require a failure_reason")
        return self


class ExperimentLogPayload(BaseModel):
    """Reusable v0.6 Experiment Log JSON artifact."""

    model_config = ConfigDict(extra="forbid")

    experiment_id: str = Field(min_length=1, pattern=r"^[A-Za-z0-9._-]+$")
    date: date
    title: str
    hypothesis: str
    environment: dict[str, str]
    parameters: dict[str, JsonValue]
    commands: list[str]
    result: str
    interpretation: str
    failure_reason: str
    next_actions: list[str]
    paper_refs: list[str]
    evidence_refs: list[str]
    status: ExperimentStatus
    review_status: Literal["pending_human_review"]

    @model_validator(mode="after")
    def validate_status_details(self) -> ExperimentLogPayload:
        if self.status == "completed" and not (self.result.strip() or self.interpretation.strip()):
            raise ValueError("Completed experiments require a result or interpretation")
        if self.status in {"failed", "blocked"} and not self.failure_reason.strip():
            raise ValueError("Failed or blocked experiments require a failure_reason")
        return self


class ExperimentLogBuilder(BaseTool):
    """Normalize experiment data without writing files or interpreting results."""

    name = "experiment_log_builder"
    description = (
        "Build a strict Experiment Log JSON artifact from researcher-provided details. "
        "Generates a deterministic ID when needed, preserves paper and evidence links, "
        "and does not write files or infer missing results."
    )
    input_model = ExperimentLogBuilderInput

    def is_read_only(self, arguments: ExperimentLogBuilderInput) -> bool:
        del arguments
        return True

    async def execute(
        self,
        arguments: ExperimentLogBuilderInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del context
        experiment_log = _build_experiment_log(arguments)
        payload = experiment_log.model_dump(mode="json")
        return ToolResult(
            output=json.dumps(payload, ensure_ascii=False, indent=2),
            metadata={
                "experiment_log": payload,
                "experiment_id": experiment_log.experiment_id,
                "status": experiment_log.status,
            },
        )


def _build_experiment_log(arguments: ExperimentLogBuilderInput) -> ExperimentLogPayload:
    experiment_id = arguments.experiment_id or _deterministic_experiment_id(arguments)
    return ExperimentLogPayload(
        experiment_id=experiment_id,
        date=arguments.date,
        title=arguments.title,
        hypothesis=arguments.hypothesis,
        environment={
            _clean_text(key): _clean_text(value) for key, value in arguments.environment.items()
        },
        parameters=arguments.parameters,
        commands=arguments.commands,
        result=_clean_text(arguments.result),
        interpretation=_clean_text(arguments.interpretation),
        failure_reason=_clean_text(arguments.failure_reason),
        next_actions=arguments.next_actions,
        paper_refs=arguments.paper_refs,
        evidence_refs=arguments.evidence_refs,
        status=arguments.status,
        review_status="pending_human_review",
    )


def _deterministic_experiment_id(arguments: ExperimentLogBuilderInput) -> str:
    canonical = arguments.model_dump(mode="json", exclude={"experiment_id"})
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()[:8].upper()
    return f"EXP-{arguments.date:%Y%m%d}-{digest}"


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


__all__ = [
    "ExperimentLogBuilder",
    "ExperimentLogBuilderInput",
    "ExperimentLogPayload",
    "ExperimentStatus",
]
