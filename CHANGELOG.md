# Changelog

## 0.3.0 - 2026-03-02

### Changed

- Bumped project version baseline from `0.2.0` to `0.3.0`.
- Updated package/runtime-facing version strings in metadata and examples.

## 0.2.0 - 2026-03-01

### Breaking

- Upgraded runtime artifact schema to v2 (`config.json`, `run.json`, optional `metrics.json`, `artifacts/`).
- Experiment function contract changed to `exp_fn(ctx: RunContext) -> dict | None`.
- Success is now defined by `run.json.status == "succeeded"`.
- `ResultAnalyzer.clean_results` switched from marker-based cleanup to `statuses/predicate` API.
- v0.2 no longer reads legacy run directory formats.

### Added

- `RunContext` and `RunSummary` public dataclasses.
- `ExperimentPipeline` facade for build + run workflows.
- Experimental dynamic scheduler with bounded submission based on CPU threshold.
- Test suite for manager/runner/analyzer/pipeline.
- CI workflow for lint, tests, docs build, and package build.

### Fixed

- Completed-run filtering now checks v2 run status instead of only checking argument files.
- Config equality check now requires strict keyset equivalence.
- Analyzer CSV export now supports custom metrics filename pass-through.
- Top-level package exports now match documented usage.
- Packaging metadata now points to `README.md`.

### Docs

- Rewrote README around problem/solution/quickstart/common pitfalls/API map.
- Reorganized docs with Chinese mainline and English entry pages.
- Added v0.2 migration guide.
- Reworked examples for minimal run, parallel run, analysis, cleanup, and LLM template.
