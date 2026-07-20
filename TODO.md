# ScholarPilot TODO

This file tracks documentation and product tasks for the ScholarPilot fork. It is intentionally separate from source-level issue tracking.

## Current Tasks

- Define the minimum Experiment Log schema for v0.6.
- Define deterministic Weekly Report aggregation rules for v0.6.
- Add small JSON examples for the implemented Paper Card and Evidence Table contracts.
- Decide which legacy OpenHarness docs should remain visible during the transition.
- Identify OpenHarness commands and package names that should stay unchanged until a later code migration.

## Completed Tasks

- Defined ScholarPilot as a research assistant Agent for graduate students and researchers.
- Documented that ScholarPilot is based on OpenHarness and is not a from-scratch framework.
- Added a staged roadmap from v0.1 through v0.6.
- Added architecture documentation for the OpenHarness relationship and research-specific layers.
- Added research workflow documentation from PDF to weekly report.
- Added AI coding agent rules for future work.
- Added the read-only `paper_card_extractor` tool with focused tests.
- Added fixed-schema Paper Card JSON with empty values for missing fields.
- Added the read-only `evidence_table_extractor` tool with focused tests.
- Added page, section, source quote, confidence, trace status, and review status to evidence rows.
- Added dynamic mock PDF fixtures without committing real research papers.
- Added the read-only `literature_matrix_builder` tool with strict Evidence Table inputs.
- Added deterministic matrix rows, field coverage, exact-match detection, and evidence gaps.
- Added the read-only `related_work_draft_builder` tool.
- Added explicit evidence approval, source-location checks, and Chinese or English draft output.

## Future Feature Tasks

- Add Experiment Log creation and update workflows.
- Generate Weekly Reports from task logs and experiment logs.
- Add demo fixtures for a small set of public papers.
- Add tests for artifact schema validation.
- Add export paths for Markdown and JSON artifacts.
- Evaluate whether a ScholarPilot CLI command should wrap the inherited OpenHarness CLI.

## Documentation Tasks

- Add a runnable v0.3 demo walkthrough.
- Add example Paper Card and Evidence Table artifacts.
- Add a contributor guide section specific to research workflows.
- Add screenshots or terminal recordings after a working demo exists.
- Mark or archive legacy OpenHarness pages that are confusing for ScholarPilot users.

## Current Non-Goals

- Do not rename the Python package.
- Do not replace the OpenHarness Agent Loop, Provider, Multi-Agent, or TUI layers.
- Do not claim rule-based extraction guarantees semantic accuracy.
- Do not treat automatically located evidence as human-confirmed evidence.
- Do not claim Literature Matrix, Related Work, Experiment Log, or Weekly Report features are implemented.
