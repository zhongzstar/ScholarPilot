# ScholarPilot Research Workflow

This document describes the target research workflow for ScholarPilot. The workflow is artifact-first: each step produces a reviewable object that can feed the next step.

## 1. PDF -> Paper Card

Implementation status: v0.2 MVP is available through `paper_card_extractor`. It extracts a fixed JSON schema with local rules and leaves unavailable fields empty. Venue, year, persistence, and interactive confirmation remain planned.

Input:

- Local PDF file.
- Optional metadata from the user.
- Optional research question or reading purpose.

Process:

1. Extract text and metadata.
2. Identify paper structure.
3. Summarize the paper into a Paper Card.
4. Attach source references where possible.
5. Ask the user to confirm or correct important fields.

Paper Card fields:

- Title.
- Authors.
- Venue and year.
- Research problem.
- Main method.
- Dataset or benchmark.
- Experimental setup.
- Key results.
- Limitations.
- Relevance to the user's project.
- Open questions.

Output:

- A structured Paper Card that can be saved as Markdown or JSON.

## 2. Paper Card -> Evidence Table

Implementation status: v0.3 MVP is available through `evidence_table_extractor`. It accepts a PDF path plus an optional Paper Card. When no Paper Card is supplied, it invokes the same conservative extraction rules used by v0.2.

Input:

- One Paper Card.
- Source text from the paper.
- User-provided notes or highlights.

Process:

1. Extract claims and observations.
2. Separate direct evidence from inference.
3. Record source location for each row.
4. Add confidence and human review status.
5. Flag unsupported or ambiguous statements.

Evidence Table columns:

- Paper ID.
- Evidence ID.
- Claim or observation.
- Evidence type.
- Source location.
- Quote or source snippet.
- Model interpretation.
- Confidence.
- Human review status.

Output:

- A source-backed Evidence Table.

Current v0.3 JSON rows contain:

- Evidence ID and Paper Card field name.
- Extracted field content.
- Evidence type: direct source text or unverified.
- One-based PDF page number and normalized section name when located.
- A bounded source quote from extracted PDF text.
- Rule-match confidence and trace status.
- `pending_human_review` status; the tool does not approve its own evidence.

Current limitations:

- The tool traces Paper Card fields; it does not yet decompose prose into semantic claims or metrics.
- It does not extract figure, table, or page-coordinate references.
- PDF text extraction quality depends on `pypdf` and the PDF's embedded text layer.

## 3. Multiple Papers -> Literature Matrix

Implementation status: v0.4 MVP is available through `literature_matrix_builder`. It accepts at least two strict Evidence Table objects, aligns selected fields, and reports exact normalized matches and evidence gaps. It does not infer semantic agreement, disagreement, or topic clusters.

Input:

- Multiple Paper Cards.
- Multiple Evidence Tables.
- User-defined comparison dimensions.

Process:

1. Normalize paper metadata.
2. Compare research questions, methods, datasets, metrics, and results.
3. Identify common assumptions and disagreements.
4. Group papers by theme or contribution.
5. Mark literature gaps and reusable citation roles.

Literature Matrix dimensions:

- Topic.
- Problem setting.
- Method family.
- Dataset.
- Metric.
- Main contribution.
- Strength.
- Limitation.
- Relationship to other papers.
- Usefulness for the user's project.

Output:

- A Literature Matrix for review, discussion, and writing.

## 4. Literature Matrix -> Related Work Draft

Implementation status: v0.5 MVP is available through `related_work_draft_builder`. The caller must provide explicit `paper_id:evidence_id` approvals. Unknown, unlocated, rejected, and unapproved evidence is excluded. Output is deterministic Chinese or English template prose, not LLM-generated synthesis, and remains marked for final human review.

Input:

- Literature Matrix.
- Confirmed Evidence Table rows.
- Target writing style or venue, if known.

Process:

1. Build a section outline from themes.
2. Select evidence-backed claims.
3. Draft paragraphs by research thread.
4. Add citation placeholders only for papers in the matrix.
5. Mark weak support and missing citations.
6. Ask the user to confirm before treating the draft as usable prose.

Draft requirements:

- Do not invent citations.
- Do not make unsupported comparison claims.
- Preserve links back to evidence rows.
- Distinguish summary, comparison, and critique.

Output:

- A Related Work Draft with evidence links and revision notes.

## 5. Experiment Log -> Weekly Report

Input:

- Experiment notes.
- Commands or configurations.
- Results and failures.
- Paper links or hypotheses.
- Task status updates.

Process:

1. Record each experiment with purpose, setup, parameters, result, and conclusion.
2. Link experiments to papers, claims, or research questions.
3. Track blockers and follow-up actions.
4. Summarize the week across reading, experiments, writing, and decisions.
5. Ask the user to confirm sensitive claims or project status.

Experiment Log fields:

- Date.
- Hypothesis.
- Setup.
- Parameters.
- Command or procedure.
- Result.
- Interpretation.
- Failure reason, if any.
- Next action.

Weekly Report sections:

- Summary.
- Papers read.
- Evidence or insights collected.
- Experiments run.
- Results and failures.
- Blockers.
- Decisions.
- Next week plan.

Output:

- A Weekly Report suitable for lab meetings, advisor updates, or personal tracking.

## Quality Principles

- Every important claim should be traceable.
- Human confirmation is required for citation-sensitive text.
- Artifacts should be reusable across sessions.
- Model inference must be labeled when it goes beyond source evidence.
- The workflow should help researchers think, not replace their judgment.
