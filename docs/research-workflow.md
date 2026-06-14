# ScholarPilot Research Workflow

This document describes the target research workflow for ScholarPilot. The workflow is artifact-first: each step produces a reviewable object that can feed the next step.

## 1. PDF -> Paper Card

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

## 3. Multiple Papers -> Literature Matrix

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
