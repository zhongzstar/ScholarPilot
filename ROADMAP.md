# ScholarPilot Roadmap

This roadmap defines ScholarPilot as a research assistant Agent built on top of OpenHarness. It focuses on staged, inspectable milestones rather than broad product claims.

## v0.1: Project Positioning and Documentation

Status: complete.

Goal: make the fork understandable to GitHub visitors, collaborators, and interviewers.

Scope:

- Establish ScholarPilot as a lab research assistant Agent.
- Clearly state that the project is based on OpenHarness.
- Document the first research workflow model.
- Add project-level agent rules in `AGENTS.md`.
- Create a staged roadmap and task list.

Deliverables:

- `README.md`
- `ROADMAP.md`
- `TODO.md`
- `AGENTS.md`
- `docs/architecture.md`
- `docs/research-workflow.md`

## v0.2: PDF Import and Paper Card

Status: MVP complete.

Goal: turn one paper PDF into a structured, reviewable Paper Card.

Implemented MVP capabilities:

- Accept a local PDF path through the OpenHarness Tool registry.
- Parse PDF metadata and text locally with `pypdf`.
- Return fixed JSON fields for title, authors, abstract, research problem, method, dataset, results, limitations, and future work.
- Return empty values when rule-based extraction cannot locate a field.
- Expose source path and page count through `ToolResult.metadata`.
- Avoid Agent Loop, Provider, Multi-Agent, and TUI changes.

Deferred beyond the MVP:

- Venue, year, experiment setup, relevance, and open-question fields.
- Interactive user confirmation and artifact persistence.
- Semantic extraction guarantees.

Expected artifact:

- `PaperCard` as a structured Markdown or JSON artifact.

## v0.3: Evidence Table Traceability

Status: MVP complete.

Goal: make every important paper note traceable to evidence.

Implemented MVP capabilities:

- Accept a local PDF and an optional v0.2 Paper Card.
- Build Paper Cards automatically when one is not supplied.
- Trace non-empty research fields to page numbers, section names, and extracted PDF text.
- Distinguish located direct source text from unverified content.
- Add confidence, trace status, and pending human-review status to every row.
- Keep empty Paper Card fields separate from populated fields that cannot be located.

Deferred beyond the MVP:

- Semantic claim and metric decomposition.
- Figure, table, and coordinate-level evidence references.
- Model-inference rows and interactive human approval.

Expected artifact:

- `EvidenceTable` with source-backed rows.

## v0.4: Literature Matrix

Status: MVP complete.

Goal: compare multiple papers in a reusable literature review structure.

Implemented MVP capabilities:

- Accept at least two strict v0.3 Evidence Table JSON objects.
- Align papers across research problem, method, dataset, results, limitations, and future work.
- Preserve paper identity, source path, and evidence IDs in each matrix row.
- Report field coverage, unverified cells, missing cells, and per-paper evidence gaps.
- Detect exact normalized values shared by multiple papers.
- Support a caller-selected subset and ordering of comparison dimensions.

Deferred beyond the MVP:

- Semantic similarity, contradiction, and contribution analysis.
- Topic, method-family, and citation-role grouping.
- Metric normalization and cross-paper numerical comparison.

Expected artifact:

- `LiteratureMatrix` for multi-paper comparison.

## v0.5: Related Work Draft

Status: MVP complete.

Goal: generate an evidence-backed related work draft from the Literature Matrix.

Implemented MVP capabilities:

- Accept a strict v0.4 Literature Matrix and explicit approved evidence references.
- Reject unknown, unlocated, or rejected evidence before drafting.
- Produce field-based Chinese or English sections for problems, methods, data, results, limitations, and future work.
- Cite only papers and evidence IDs present in the supplied matrix.
- Exclude unapproved evidence and report missing or untraced matrix fields as warnings.
- Mark every output as a draft requiring final human review.

Deferred beyond the MVP:

- LLM-assisted thematic synthesis and fluent paragraph transitions.
- Citation-style rendering and bibliography manager integration.
- Interactive approval UI and persistent revision history.

Expected artifact:

- `RelatedWorkDraft` with evidence links and revision notes.

## v0.6: Experiment Log and Weekly Report

Status: MVP complete.

Goal: connect reading, experimentation, and reporting.

Implemented MVP capabilities:

- Build strict Experiment Log JSON from user-supplied hypothesis, environment, parameters, commands, outcomes, failures, and next actions.
- Generate deterministic experiment IDs when the caller does not provide one.
- Preserve paper IDs and evidence references beside experiments.
- Validate completed, failed, and blocked experiment records without inventing missing outcomes.
- Aggregate paper readings, Experiment Logs, task updates, blockers, decisions, and plans into a Weekly Report.
- Return both strict Weekly Report JSON and deterministic Chinese or English Markdown.
- Validate reporting periods, experiment dates, duplicate IDs, and structured status counts.

Deferred beyond the MVP:

- Persistent Experiment Log creation and in-place updates.
- Automatic ingestion from OpenHarness task/session logs.
- Scheduled report generation and delivery.
- LLM-assisted narrative synthesis of experiment results.

Expected artifacts:

- `ExperimentLog`
- `WeeklyReport`

## Beyond v0.6

Possible later directions:

- Research project memory and long-term lab context.
- Citation manager integration.
- Dataset and benchmark cards.
- Figure/table extraction and comparison.
- Multi-agent review workflows for draft critique.
- Export to Markdown, Word, LaTeX, or project notebooks.
