# Changelog

## 1.0.0 - 2026-03-02

### Breaking

- None.

### Added

- None.

### Fixed

- Fixed release ordering confusion caused by historical `0.30.0` and `0.4.0` coexistence.
- Normalized package versioning baseline to `1.0.0` to ensure unambiguous upgrade ordering on package index.

### Docs

- None.

### Migration

- Users on `0.30.0` / `0.4.0` can upgrade directly to `1.0.0` with:
  - `pip install -U ztxexp`

## 0.4.0 - 2026-03-02

### Breaking

- None.

### Added

- Added reproducibility/governance dataclasses:
  - `RunMetadata`
  - `MetricEvent`
- Added `RunContext` enhancements:
  - `meta`
  - `log_metric(step, metrics, split, phase)`
- Added run artifact extensions (schema v2 compatible):
  - `meta.json`
  - `metrics.jsonl`
  - `events.jsonl`
  - `checkpoints/`
- Added `ExperimentPipeline` governance APIs:
  - `name(...)`, `group(...)`, `tags(...)`, `lineage(...)`
  - `retry(...)`, `track(...)`, `random_search(...)`
- Added tracker system:
  - `Tracker` protocol
  - built-in `JsonlTracker`
  - optional `MlflowTracker` / `WandbTracker` adapters
- Added CI workflow:
  - `ruff check .`
  - `pytest`
  - `mkdocs build --strict`
  - `python -m build --no-isolation`
  - `twine check dist/*`
- Added migration guide:
  - `docs_src/migration-v04.zh.md`
- Added template smoke test suite:
  - `tests/test_templates_smoke.py`

### Fixed

- Fixed docs build hard-failure by restoring `docs_src/` directory.
- Fixed mismatch between changelog quality claims and actual CI presence.
- Improved analyzer query capability with `experiment_name/group/tags` filters.
- Improved template docs generation with scenario copy matrix page.
- Refined dependency layering: `mlflow/wandb` remain optional extras and are no longer installed via `dev` by default.

### Docs

- README now includes v0.4 governance and reproducibility features.
- Template docs now include `场景复制矩阵` for direct copy commands.

### Migration

- Existing `0.3` API usage remains valid; upgrades are additive.
- Recommended migration:
  1. Add governance metadata (`name/group/tags/lineage`).
  2. Replace manual step logs with `ctx.log_metric(...)`.
  3. Enable optional trackers via extras when needed.

## 0.3.0 - 2026-03-02

### Changed

- Bumped project version baseline from `0.2.0` to `0.3.0`.
- Updated package/runtime-facing version strings in metadata and examples.

### Added

- Added a copy-first template library under `examples/template_library` with 27 runnable templates.
- Added scenario coverage across basics, parallel scheduling, analysis/cleanup, ML, LLM, and ops workflows.
- Added automatic MkDocs template pages generation (`示例模板库`) from template source files.

### Docs

- README now highlights template-library-first workflow and direct copy paths.
- Template index table is generated and available in docs navigation.

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
