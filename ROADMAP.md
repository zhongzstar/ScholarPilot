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

Status: planned.

Goal: generate an evidence-backed related work draft from the Literature Matrix.

Planned capabilities:

- Produce a structured related work outline.
- Draft paragraphs grouped by research thread.
- Cite only papers present in the matrix.
- Keep claims linked to evidence rows.
- Mark weak or missing evidence instead of fabricating support.
- Ask for human confirmation before finalizing citation-sensitive text.

Expected artifact:

- `RelatedWorkDraft` with evidence links and revision notes.

## v0.6: Experiment Log and Weekly Report

Status: planned.

Goal: connect reading, experimentation, and reporting.

Planned capabilities:

- Record experiment hypothesis, environment, parameters, commands, results, failures, and follow-up actions.
- Link experiments to papers, claims, or open research questions.
- Generate weekly summaries of readings, experiments, blockers, decisions, and next steps.
- Keep task logs auditable across sessions.
- Support lab meeting preparation from accumulated logs.

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
