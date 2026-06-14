# ScholarPilot TODO

This file tracks documentation and product tasks for the ScholarPilot fork. It is intentionally separate from source-level issue tracking.

## Current Tasks

- Review v0.1 documentation for accuracy and scope control.
- Decide whether the first implementation should store Paper Cards as Markdown, JSON, or both.
- Define the minimum Paper Card schema for v0.2.
- Define the minimum Evidence Table schema for v0.3.
- Decide which legacy OpenHarness docs should remain visible during the transition.
- Identify OpenHarness commands and package names that should stay unchanged until a later code migration.

## Completed Tasks

- Defined ScholarPilot as a research assistant Agent for graduate students and researchers.
- Documented that ScholarPilot is based on OpenHarness and is not a from-scratch framework.
- Added a staged roadmap from v0.1 through v0.6.
- Added architecture documentation for the OpenHarness relationship and research-specific layers.
- Added research workflow documentation from PDF to weekly report.
- Added AI coding agent rules for future work.

## Future Feature Tasks

- Implement PDF ingestion for local files.
- Generate structured Paper Cards.
- Add source references to Paper Card fields.
- Implement Evidence Table extraction and validation.
- Add confidence, source type, and human review status to evidence rows.
- Build Literature Matrix generation from multiple Paper Cards.
- Generate Related Work Drafts only from confirmed evidence.
- Add Experiment Log creation and update workflows.
- Generate Weekly Reports from task logs and experiment logs.
- Add demo fixtures for a small set of public papers.
- Add tests for artifact schema validation.
- Add export paths for Markdown and JSON artifacts.
- Evaluate whether a ScholarPilot CLI command should wrap the inherited OpenHarness CLI.

## Documentation Tasks

- Add a demo walkthrough after v0.2 lands.
- Add example Paper Card and Evidence Table artifacts.
- Add a contributor guide section specific to research workflows.
- Add screenshots or terminal recordings after a working demo exists.
- Mark or archive legacy OpenHarness pages that are confusing for ScholarPilot users.

## Non-Goals for v0.1

- Do not rename the Python package.
- Do not modify `src/openharness`.
- Do not modify `tests`.
- Do not modify `ohmo`, `frontend`, or `scripts`.
- Do not claim PDF, Evidence Table, or writing features are already implemented.
