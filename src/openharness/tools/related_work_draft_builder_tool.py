"""Build a citation-linked Related Work draft from approved matrix evidence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult
from openharness.tools.literature_matrix_builder_tool import (
    LiteratureMatrixPayload,
    LiteratureMatrixRowPayload,
    MatrixCellPayload,
    MatrixDimension,
)


DraftLanguage = Literal["zh", "en"]

RELATED_WORK_DRAFT_KEYS = (
    "title",
    "language",
    "sections",
    "used_evidence",
    "excluded_evidence",
    "warnings",
    "review_status",
)

_SECTION_LAYOUT: tuple[tuple[str, tuple[MatrixDimension, ...]], ...] = (
    ("research_context", ("research_problem",)),
    ("methods", ("method",)),
    ("data_and_results", ("dataset", "results")),
    ("limitations_and_directions", ("limitations", "future_work")),
)

_ZH_LABELS = {
    "research_problem": "研究问题",
    "method": "研究方法",
    "dataset": "数据集",
    "results": "研究结果",
    "limitations": "研究局限",
    "future_work": "未来工作",
}

_EN_LABELS = {
    "research_problem": "research problem",
    "method": "method",
    "dataset": "dataset",
    "results": "results",
    "limitations": "limitations",
    "future_work": "future work",
}

_ZH_HEADINGS = {
    "research_context": "研究背景与问题",
    "methods": "研究方法",
    "data_and_results": "数据与结果",
    "limitations_and_directions": "局限与未来方向",
}

_EN_HEADINGS = {
    "research_context": "Research Context and Problems",
    "methods": "Methods",
    "data_and_results": "Data and Results",
    "limitations_and_directions": "Limitations and Future Directions",
}


class DraftCitationPayload(BaseModel):
    """Citation metadata retained beside a generated paragraph."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str
    evidence_refs: list[str] = Field(min_length=1)


class DraftParagraphPayload(BaseModel):
    """One deterministic paragraph for a matrix dimension."""

    model_config = ConfigDict(extra="forbid")

    dimension: MatrixDimension
    text: str
    citations: list[DraftCitationPayload] = Field(min_length=1)


class DraftSectionPayload(BaseModel):
    """A field-based Related Work section."""

    model_config = ConfigDict(extra="forbid")

    heading: str
    paragraphs: list[DraftParagraphPayload] = Field(min_length=1)


class RelatedWorkDraftPayload(BaseModel):
    """Reusable v0.5 draft artifact with evidence links."""

    model_config = ConfigDict(extra="forbid")

    title: str
    language: DraftLanguage
    sections: list[DraftSectionPayload]
    used_evidence: list[str]
    excluded_evidence: list[str]
    warnings: list[str]
    review_status: Literal["draft_requires_final_review"]


class RelatedWorkDraftBuilderInput(BaseModel):
    """Arguments for drafting only from explicitly approved evidence."""

    literature_matrix: LiteratureMatrixPayload
    approved_evidence_refs: list[str] = Field(min_length=1)
    language: DraftLanguage = "zh"

    @field_validator("approved_evidence_refs")
    @classmethod
    def validate_approved_refs(cls, value: list[str]) -> list[str]:
        cleaned = [reference.strip() for reference in value]
        if any(not reference or ":" not in reference for reference in cleaned):
            raise ValueError("Evidence references must use the form paper_id:evidence_id")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Approved evidence references must be unique")
        return cleaned


class RelatedWorkDraftBuilder(BaseTool):
    """Create template prose from approved, source-located evidence only."""

    name = "related_work_draft_builder"
    description = (
        "Build a Chinese or English Related Work draft from a Literature Matrix. Only "
        "explicitly approved, source-located evidence references are used; unknown, "
        "unverified, rejected, and unapproved evidence is excluded."
    )
    input_model = RelatedWorkDraftBuilderInput

    def is_read_only(self, arguments: RelatedWorkDraftBuilderInput) -> bool:
        del arguments
        return True

    async def execute(
        self,
        arguments: RelatedWorkDraftBuilderInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del context
        evidence_index = _index_evidence(arguments.literature_matrix)
        approved = arguments.approved_evidence_refs

        unknown = [reference for reference in approved if reference not in evidence_index]
        if unknown:
            return ToolResult(
                output="Unknown evidence references: " + ", ".join(unknown),
                is_error=True,
            )

        untraceable = [
            reference
            for reference in approved
            if evidence_index[reference].cell.trace_status != "located"
        ]
        if untraceable:
            return ToolResult(
                output="Approved evidence is not source-located: " + ", ".join(untraceable),
                is_error=True,
            )

        rejected = [
            reference
            for reference in approved
            if evidence_index[reference].cell.review_status == "rejected"
        ]
        if rejected:
            return ToolResult(
                output="Rejected evidence cannot be used: " + ", ".join(rejected),
                is_error=True,
            )

        draft = _build_related_work_draft(
            matrix=arguments.literature_matrix,
            evidence_index=evidence_index,
            approved_refs=approved,
            language=arguments.language,
        )
        payload = draft.model_dump(mode="json")
        return ToolResult(
            output=json.dumps(payload, ensure_ascii=False, indent=2),
            metadata={
                "related_work_draft": payload,
                "used_evidence": list(draft.used_evidence),
                "language": draft.language,
            },
        )


@dataclass(frozen=True)
class _IndexedEvidence:
    row: LiteratureMatrixRowPayload
    dimension: MatrixDimension
    cell: MatrixCellPayload


def _index_evidence(matrix: LiteratureMatrixPayload) -> dict[str, _IndexedEvidence]:
    index: dict[str, _IndexedEvidence] = {}
    for row in matrix.rows:
        for dimension in matrix.dimensions:
            cell = row.cells[dimension]
            for evidence_id in cell.evidence_ids:
                reference = f"{row.paper_id}:{evidence_id}"
                if reference in index:
                    raise ValueError(f"Duplicate matrix evidence reference: {reference}")
                index[reference] = _IndexedEvidence(row, dimension, cell)
    return index


def _build_related_work_draft(
    matrix: LiteratureMatrixPayload,
    evidence_index: dict[str, _IndexedEvidence],
    approved_refs: list[str],
    language: DraftLanguage,
) -> RelatedWorkDraftPayload:
    approved_set = set(approved_refs)
    sections: list[DraftSectionPayload] = []

    for section_key, dimensions in _SECTION_LAYOUT:
        paragraphs = [
            paragraph
            for dimension in dimensions
            if dimension in matrix.dimensions
            if (paragraph := _draft_dimension(matrix, dimension, approved_set, language))
            is not None
        ]
        if paragraphs:
            headings = _ZH_HEADINGS if language == "zh" else _EN_HEADINGS
            sections.append(
                DraftSectionPayload(
                    heading=headings[section_key],
                    paragraphs=paragraphs,
                )
            )

    all_references = list(evidence_index)
    excluded = [reference for reference in all_references if reference not in approved_set]
    warnings = _draft_warnings(matrix, excluded, language)
    return RelatedWorkDraftPayload(
        title="相关工作草稿" if language == "zh" else "Related Work Draft",
        language=language,
        sections=sections,
        used_evidence=approved_refs,
        excluded_evidence=excluded,
        warnings=warnings,
        review_status="draft_requires_final_review",
    )


def _draft_dimension(
    matrix: LiteratureMatrixPayload,
    dimension: MatrixDimension,
    approved_refs: set[str],
    language: DraftLanguage,
) -> DraftParagraphPayload | None:
    sentences: list[str] = []
    citations: list[DraftCitationPayload] = []

    for row in matrix.rows:
        cell = row.cells[dimension]
        references = [
            f"{row.paper_id}:{evidence_id}"
            for evidence_id in cell.evidence_ids
            if f"{row.paper_id}:{evidence_id}" in approved_refs
        ]
        if not references:
            continue

        sentences.append(_draft_sentence(row, dimension, cell.content, language))
        citations.append(
            DraftCitationPayload(
                paper_id=row.paper_id,
                title=row.title,
                evidence_refs=references,
            )
        )

    if not sentences:
        return None
    return DraftParagraphPayload(
        dimension=dimension,
        text=" ".join(sentences),
        citations=citations,
    )


def _draft_sentence(
    row: LiteratureMatrixRowPayload,
    dimension: MatrixDimension,
    content: str,
    language: DraftLanguage,
) -> str:
    if language == "zh":
        return f"《{row.title}》在{_ZH_LABELS[dimension]}方面记录为：{content} [{row.paper_id}]。"
    return f"{row.title} reports the following for {_EN_LABELS[dimension]}: {content} [{row.paper_id}]."


def _draft_warnings(
    matrix: LiteratureMatrixPayload,
    excluded: list[str],
    language: DraftLanguage,
) -> list[str]:
    warnings: list[str] = []
    if matrix.comparison.evidence_gaps:
        warnings.append(
            "矩阵中的缺失或未溯源字段未进入草稿。"
            if language == "zh"
            else "Missing or untraced matrix fields were not drafted."
        )
    if excluded:
        warnings.append(
            f"{len(excluded)} 条未批准证据已排除。"
            if language == "zh"
            else f"{len(excluded)} unapproved evidence references were excluded."
        )
    warnings.append(
        "该草稿由固定模板生成，引用和表述仍需人工复核。"
        if language == "zh"
        else "This template-generated draft still requires human review of citations and wording."
    )
    return warnings


__all__ = [
    "RelatedWorkDraftBuilder",
    "RelatedWorkDraftBuilderInput",
    "RelatedWorkDraftPayload",
]
