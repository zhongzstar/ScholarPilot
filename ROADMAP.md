# ScholarPilot Roadmap

This roadmap defines ScholarPilot as a research assistant Agent built on top of OpenHarness. It focuses on staged, inspectable milestones rather than broad product claims.

## v0.1: Project Positioning and Documentation

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

Goal: turn one paper PDF into a structured, reviewable Paper Card.

Planned capabilities:

- Accept a local PDF path or paper metadata.
- Extract title, authors, venue, year, abstract, and sections when available.
- Generate a Paper Card with problem, method, dataset, experiment setup, key results, limitations, and relevance.
- Preserve source references such as page number, section name, or extracted text span.
- Require user confirmation before saving a Paper Card.

Expected artifact:

- `PaperCard` as a structured Markdown or JSON artifact.

## v0.3: Evidence Table Traceability

Goal: make every important paper note traceable to evidence.

Planned capabilities:

- Extract claims, methods, datasets, metrics, findings, and limitations into rows.
- Attach each row to page references, section names, quotes, figures, or tables.
- Mark confidence and source quality.
- Separate direct evidence from model inference.
- Flag unsupported claims for human review.

Expected artifact:

- `EvidenceTable` with source-backed rows.

## v0.4: Literature Matrix

Goal: compare multiple papers in a reusable literature review structure.

Planned capabilities:

- Merge multiple Paper Cards and Evidence Tables.
- Compare research questions, methods, datasets, metrics, assumptions, strengths, and weaknesses.
- Group papers by topic, method, task, or contribution type.
- Identify agreement, disagreement, gaps, and reusable citation roles.
- Export matrix rows for writing or lab discussion.

Expected artifact:

- `LiteratureMatrix` for multi-paper comparison.

## v0.5: Related Work Draft

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
