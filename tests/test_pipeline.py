from __future__ import annotations

from ztxexp import (
    ExperimentPipeline,
    ExpManager,
    ExpRunner,
    JsonlTracker,
    MetricEvent,
    ResultAnalyzer,
    RunContext,
    RunMetadata,
    RunSummary,
)


def exp_fn(ctx: RunContext):
    return {"score": 1.0 - ctx.config["lr"]}


def test_public_exports_are_importable():
    assert ExpManager is not None
    assert ExpRunner is not None
    assert ResultAnalyzer is not None
    assert ExperimentPipeline is not None
    assert RunContext is not None
    assert RunMetadata is not None
    assert MetricEvent is not None
    assert RunSummary is not None
    assert JsonlTracker is not None


def test_pipeline_build_and_run_with_exclude_completed(tmp_path):
    pipeline = (
        ExperimentPipeline(tmp_path, base_config={"seed": 42})
        .grid({"lr": [0.001, 0.01]})
        .variants([{"model": "tiny"}])
        .exclude_completed()
    )

    first = pipeline.run(exp_fn, mode="sequential")
    assert first.total == 2
    assert first.succeeded == 2

    second = pipeline.run(exp_fn, mode="sequential")
    assert second.total == 0
    assert second.succeeded == 0


def test_pipeline_extended_controls(tmp_path):
    pipeline = (
        ExperimentPipeline(tmp_path, base_config={"seed": 42, "dataset_version": "v2"})
        .name("demo_exp")
        .group("nightly")
        .tags({"owner": "ci"})
        .lineage("parent_001")
        .retry(max_attempts=2, retry_on=("RuntimeError",))
        .random_search({"lr": [0.001, 0.01]}, n_trials=2, seed=7)
        .track("jsonl")
    )

    summary = pipeline.run(exp_fn, mode="sequential")
    assert summary.total == 2
    assert summary.succeeded == 2
