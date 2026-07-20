"""Build a conservative comparison matrix from Evidence Tables."""

from __future__ import annotations

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from openharness.tools.base import BaseTool, ToolExecutionContext, ToolResult


EvidenceFieldName = Literal[
    "abstract",
    "research_problem",
    "method",
    "dataset",
    "results",
    "limitations",
    "future_work",
]
MatrixDimension = Literal[
    "research_problem",
    "method",
    "dataset",
    "results",
    "limitations",
    "future_work",
]

MATRIX_DIMENSIONS: tuple[MatrixDimension, ...] = (
    "research_problem",
    "method",
    "dataset",
    "results",
    "limitations",
    "future_work",
)

LITERATURE_MATRIX_KEYS = (
    "dimensions",
    "rows",
    "comparison",
)

MATRIX_ROW_KEYS = (
    "paper_id",
    "title",
    "authors",
    "source_path",
    "cells",
)

MATRIX_CELL_KEYS = (
    "content",
    "evidence_ids",
    "trace_status",
    "review_status",
)


class EvidencePaperPayload(BaseModel):
    """Paper identity embedded in a v0.3 Evidence Table."""

    model_config = ConfigDict(extra="forbid")

    title: str = ""
    authors: list[str] = Field(default_factory=list)


class EvidenceRowPayload(BaseModel):
    """One source-traceable row accepted from v0.3."""

    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    field: EvidenceFieldName
    content: str
    evidence_type: Literal["direct_source_text", "unverified"]
    page_number: int | None = Field(default=None, ge=1)
    section: str
    source_quote: str
    confidence: Literal["high", "medium", "none"]
    trace_status: Literal["located", "not_located"]
    review_status: Literal["pending_human_review", "confirmed", "rejected"]


class EvidenceTablePayload(BaseModel):
    """Strict input contract matching the v0.3 JSON artifact."""

    model_config = ConfigDict(extra="forbid")

    paper: EvidencePaperPayload
    source_path: str
    page_count: int = Field(ge=0)
    rows: list[EvidenceRowPayload] = Field(default_factory=list)
    missing_fields: list[EvidenceFieldName] = Field(default_factory=list)
    unverified_fields: list[EvidenceFieldName] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_rows(self) -> EvidenceTablePayload:
        evidence_ids = [row.evidence_id for row in self.rows]
        fields = [row.field for row in self.rows]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Evidence Table evidence_id values must be unique")
        if len(fields) != len(set(fields)):
            raise ValueError("Evidence Table fields must be unique")
        return self


class MatrixCellPayload(BaseModel):
    """One paper-by-dimension matrix cell."""

    model_config = ConfigDict(extra="forbid")

    content: str
    evidence_ids: list[str]
    trace_status: Literal["located", "not_located", "missing"]
    review_status: Literal[
        "pending_human_review",
        "confirmed",
        "rejected",
        "not_applicable",
    ]


class LiteratureMatrixRowPayload(BaseModel):
    """One paper aligned across selected dimensions."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    title: str
    authors: list[str]
    source_path: str
    cells: dict[MatrixDimension, MatrixCellPayload]


class FieldCoveragePayload(BaseModel):
    """Coverage counts for one comparison dimension."""

    model_config = ConfigDict(extra="forbid")

    populated: int = Field(ge=0)
    located: int = Field(ge=0)
    unverified: int = Field(ge=0)
    missing: int = Field(ge=0)


class ExactMatchPayload(BaseModel):
    """An exact normalized value shared by multiple papers."""

    model_config = ConfigDict(extra="forbid")

    dimension: MatrixDimension
    content: str
    paper_ids: list[str] = Field(min_length=2)


class EvidenceGapPayload(BaseModel):
    """Missing or unverified dimensions for one paper."""

    model_config = ConfigDict(extra="forbid")

    paper_id: str
    fields: list[MatrixDimension]


class MatrixComparisonPayload(BaseModel):
    """Mechanical comparison summary with no semantic inference."""

    model_config = ConfigDict(extra="forbid")

    paper_count: int = Field(ge=2)
    field_coverage: dict[MatrixDimension, FieldCoveragePayload]
    exact_matches: list[ExactMatchPayload]
    evidence_gaps: list[EvidenceGapPayload]


class LiteratureMatrixPayload(BaseModel):
    """Reusable v0.4 Literature Matrix artifact."""

    model_config = ConfigDict(extra="forbid")

    dimensions: list[MatrixDimension]
    rows: list[LiteratureMatrixRowPayload] = Field(min_length=2)
    comparison: MatrixComparisonPayload

    @model_validator(mode="after")
    def validate_matrix_contract(self) -> LiteratureMatrixPayload:
        if not self.dimensions or len(self.dimensions) != len(set(self.dimensions)):
            raise ValueError("Literature Matrix dimensions must be non-empty and unique")
        paper_ids = [row.paper_id for row in self.rows]
        if len(paper_ids) != len(set(paper_ids)):
            raise ValueError("Literature Matrix paper_id values must be unique")
        expected_dimensions = set(self.dimensions)
        for row in self.rows:
            if set(row.cells) != expected_dimensions:
                raise ValueError("Each Literature Matrix row must contain every selected dimension")
            evidence_ids = [
                evidence_id for cell in row.cells.values() for evidence_id in cell.evidence_ids
            ]
            if len(evidence_ids) != len(set(evidence_ids)):
                raise ValueError("Evidence IDs must be unique within each Literature Matrix row")
        return self


class LiteratureMatrixBuilderInput(BaseModel):
    """Arguments for aligning multiple Evidence Tables."""

    evidence_tables: list[EvidenceTablePayload] = Field(min_length=2)
    dimensions: list[MatrixDimension] = Field(default_factory=lambda: list(MATRIX_DIMENSIONS))

    @field_validator("dimensions")
    @classmethod
    def validate_dimensions(cls, value: list[MatrixDimension]) -> list[MatrixDimension]:
        if not value:
            raise ValueError("At least one matrix dimension is required")
        if len(value) != len(set(value)):
            raise ValueError("Matrix dimensions must be unique")
        return value


class LiteratureMatrixBuilder(BaseTool):
    """Align Evidence Tables without inventing semantic comparisons."""

    name = "literature_matrix_builder"
    description = (
        "Build a Literature Matrix from at least two Evidence Tables. Reports field "
        "coverage, exact normalized matches, and evidence gaps without using an LLM "
        "or claiming semantic similarity."
    )
    input_model = LiteratureMatrixBuilderInput

    def is_read_only(self, arguments: LiteratureMatrixBuilderInput) -> bool:
        del arguments
        return True

    async def execute(
        self,
        arguments: LiteratureMatrixBuilderInput,
        context: ToolExecutionContext,
    ) -> ToolResult:
        del context
        matrix = _build_literature_matrix(arguments.evidence_tables, arguments.dimensions)
        payload = matrix.model_dump(mode="json")
        return ToolResult(
            output=json.dumps(payload, ensure_ascii=False, indent=2),
            metadata={
                "literature_matrix": payload,
                "paper_count": len(matrix.rows),
                "dimensions": list(matrix.dimensions),
            },
        )


def _build_literature_matrix(
    evidence_tables: list[EvidenceTablePayload],
    dimensions: list[MatrixDimension],
) -> LiteratureMatrixPayload:
    matrix_rows = [
        _build_matrix_row(index, table, dimensions)
        for index, table in enumerate(evidence_tables, start=1)
    ]
    comparison = MatrixComparisonPayload(
        paper_count=len(matrix_rows),
        field_coverage=_field_coverage(matrix_rows, dimensions),
        exact_matches=_exact_matches(matrix_rows, dimensions),
        evidence_gaps=_evidence_gaps(matrix_rows, dimensions),
    )
    return LiteratureMatrixPayload(
        dimensions=dimensions,
        rows=matrix_rows,
        comparison=comparison,
    )


def _build_matrix_row(
    index: int,
    table: EvidenceTablePayload,
    dimensions: list[MatrixDimension],
) -> LiteratureMatrixRowPayload:
    evidence_by_field = {row.field: row for row in table.rows}
    cells: dict[MatrixDimension, MatrixCellPayload] = {}

    for dimension in dimensions:
        evidence = evidence_by_field.get(dimension)
        if evidence is None:
            cells[dimension] = MatrixCellPayload(
                content="",
                evidence_ids=[],
                trace_status="missing",
                review_status="not_applicable",
            )
            continue

        cells[dimension] = MatrixCellPayload(
            content=_normalize_display_text(evidence.content),
            evidence_ids=[evidence.evidence_id],
            trace_status=evidence.trace_status,
            review_status=evidence.review_status,
        )

    return LiteratureMatrixRowPayload(
        paper_id=f"P{index:03d}",
        title=_normalize_display_text(table.paper.title),
        authors=table.paper.authors,
        source_path=table.source_path,
        cells=cells,
    )


def _field_coverage(
    rows: list[LiteratureMatrixRowPayload],
    dimensions: list[MatrixDimension],
) -> dict[MatrixDimension, FieldCoveragePayload]:
    coverage: dict[MatrixDimension, FieldCoveragePayload] = {}
    for dimension in dimensions:
        cells = [row.cells[dimension] for row in rows]
        coverage[dimension] = FieldCoveragePayload(
            populated=sum(bool(cell.content) for cell in cells),
            located=sum(cell.trace_status == "located" for cell in cells),
            unverified=sum(cell.trace_status == "not_located" for cell in cells),
            missing=sum(cell.trace_status == "missing" for cell in cells),
        )
    return coverage


def _exact_matches(
    rows: list[LiteratureMatrixRowPayload],
    dimensions: list[MatrixDimension],
) -> list[ExactMatchPayload]:
    matches: list[ExactMatchPayload] = []
    for dimension in dimensions:
        grouped: dict[str, tuple[str, list[str]]] = {}
        for row in rows:
            cell = row.cells[dimension]
            if cell.trace_status != "located" or not cell.content:
                continue
            normalized = _comparison_key(cell.content)
            if normalized not in grouped:
                grouped[normalized] = (cell.content, [])
            grouped[normalized][1].append(row.paper_id)

        for content, paper_ids in grouped.values():
            if len(paper_ids) >= 2:
                matches.append(
                    ExactMatchPayload(
                        dimension=dimension,
                        content=content,
                        paper_ids=paper_ids,
                    )
                )
    return matches


def _evidence_gaps(
    rows: list[LiteratureMatrixRowPayload],
    dimensions: list[MatrixDimension],
) -> list[EvidenceGapPayload]:
    gaps: list[EvidenceGapPayload] = []
    for row in rows:
        fields = [
            dimension for dimension in dimensions if row.cells[dimension].trace_status != "located"
        ]
        if fields:
            gaps.append(EvidenceGapPayload(paper_id=row.paper_id, fields=fields))
    return gaps


def _normalize_display_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _comparison_key(value: str) -> str:
    return _normalize_display_text(value).casefold()


__all__ = [
    "EvidenceTablePayload",
    "LiteratureMatrixBuilder",
    "LiteratureMatrixBuilderInput",
    "LiteratureMatrixPayload",
    "MatrixCellPayload",
    "MatrixDimension",
]
