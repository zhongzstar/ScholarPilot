# AGENTS.md

This file gives AI coding agents the project rules for working in ScholarPilot.

## Project Goal

ScholarPilot is a lab research assistant Agent based on OpenHarness. The goal is to adapt the inherited OpenHarness runtime into a research workflow assistant for paper reading, literature organization, evidence tracking, experiment logs, and research writing.

The project must be presented honestly as a second-stage development fork. Do not describe it as a from-scratch agent framework.

## Protected Scope

Unless the user explicitly requests a code task, do not modify:

- `src/`
- `tests/`
- `ohmo/`
- `frontend/`
- `scripts/`
- `autopilot-dashboard/`
- `.github/workflows/`
- `LICENSE`

The original license must remain in place.

For documentation-only tasks, stay within the files explicitly named by the user.

## Working Rules

- Read the existing files before editing.
- Keep changes scoped to the task.
- Preserve user changes already present in the working tree.
- Do not revert unrelated modifications.
- State clearly when a feature is planned rather than implemented.
- Keep the OpenHarness fork relationship visible in user-facing docs.
- Prefer small, reviewable changes over broad rewrites.
- When adding research workflow docs, distinguish source evidence, model inference, and human confirmation.

## Documentation Rules

- Use GitHub-friendly Markdown.
- Make the README understandable to a reviewer in a few minutes.
- Do not overstate implementation status.
- Include concrete artifacts such as Paper Card, Evidence Table, Literature Matrix, Related Work Draft, Experiment Log, and Weekly Report when relevant.
- Link to supporting docs instead of duplicating every detail in the README.

## Testing Requirements

For documentation-only changes:

- Run a status check to confirm the changed files are the intended docs.
- Search for accidental claims that planned features are already complete.
- No source tests are required unless documentation examples execute code.

For future code changes:

- Add or update focused tests for the changed behavior.
- Run the smallest relevant test set first.
- Run broader tests when touching shared OpenHarness runtime paths.
- Report any tests that could not be run.

## Commit Requirements

- Do not create commits unless the user asks.
- If asked to commit, review `git status` first.
- Do not stage unrelated user changes.
- Use a commit message that names the user-visible purpose, for example `docs: define ScholarPilot v0.1 positioning`.
