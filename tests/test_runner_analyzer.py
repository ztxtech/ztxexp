from __future__ import annotations

from ztxexp import ResultAnalyzer
from ztxexp.constants import RUN_SCHEMA_VERSION, RUN_STATUS_FAILED, RUN_STATUS_SUCCEEDED
from ztxexp.runner import ExpRunner
from ztxexp.types import RunContext
from ztxexp.utils import load_json


def exp_ok(ctx: RunContext):
    return {"score": round(1.0 - float(ctx.config.get("lr", 0.0)), 4)}


def exp_maybe_fail(ctx: RunContext):
    if ctx.config.get("fail"):
        raise RuntimeError("intentional failure")
    return {"score": 0.9}


def exp_invalid_return(ctx: RunContext):
    if ctx.config.get("bad"):
        return 123
    return {"score": 0.8}


def test_runner_sequential_writes_v2_artifacts(tmp_path):
    runner = ExpRunner(configs=[{"lr": 0.001}, {"lr": 0.01}], results_root=tmp_path)
    summary = runner.run(exp_ok, mode="sequential")

    assert summary.total == 2
    assert summary.succeeded == 2
    assert summary.failed == 0

    run_dirs = sorted([p for p in tmp_path.iterdir() if p.is_dir()])
    assert len(run_dirs) == 2

    for run_dir in run_dirs:
        assert (run_dir / "config.json").exists()
        assert (run_dir / "run.json").exists()
        assert (run_dir / "metrics.json").exists()
        assert (run_dir / "artifacts").exists()
        meta = load_json(run_dir / "run.json")
        assert meta["schema_version"] == RUN_SCHEMA_VERSION
        assert meta["status"] == RUN_STATUS_SUCCEEDED


def test_runner_marks_invalid_return_as_failed(tmp_path):
    runner = ExpRunner(
        configs=[{"bad": True}, {"bad": False}],
        results_root=tmp_path,
    )
    summary = runner.run(exp_invalid_return, mode="sequential")

    assert summary.total == 2
    assert summary.failed == 1

    failed_dirs = []
    for run_dir in tmp_path.iterdir():
        if not run_dir.is_dir():
            continue
        meta = load_json(run_dir / "run.json")
        if meta["status"] == RUN_STATUS_FAILED:
            failed_dirs.append(run_dir)

    assert len(failed_dirs) == 1
    assert (failed_dirs[0] / "error.log").exists()


def test_runner_process_pool_joblib_dynamic(tmp_path):
    configs = [{"lr": 0.001}, {"lr": 0.01}, {"lr": 0.02}]

    summary_pool = ExpRunner(configs, tmp_path / "pool").run(exp_ok, mode="process_pool", workers=2)
    assert summary_pool.total == 3
    assert summary_pool.failed == 0

    summary_joblib = ExpRunner(configs, tmp_path / "joblib").run(exp_ok, mode="joblib", workers=2)
    assert summary_joblib.total == 3
    assert summary_joblib.failed == 0

    summary_dynamic = ExpRunner(configs, tmp_path / "dynamic").run(
        exp_ok,
        mode="dynamic",
        workers=2,
        cpu_threshold=100,
    )
    assert summary_dynamic.total == 3
    assert summary_dynamic.failed == 0


def test_analyzer_merge_and_cleanup(tmp_path):
    runner = ExpRunner(
        configs=[{"lr": 0.001, "fail": False}, {"lr": 0.01, "fail": True}],
        results_root=tmp_path,
    )
    runner.run(exp_maybe_fail, mode="sequential")

    analyzer = ResultAnalyzer(tmp_path)

    all_df = analyzer.to_dataframe(statuses=None)
    assert len(all_df) == 2
    assert "lr" in all_df.columns
    assert "status" in all_df.columns

    success_df = analyzer.to_dataframe(statuses=(RUN_STATUS_SUCCEEDED,))
    assert len(success_df) == 1

    failed_df = analyzer.to_dataframe(statuses=(RUN_STATUS_FAILED,))
    assert len(failed_df) == 1

    would_delete = analyzer.clean_results(
        statuses=None,
        predicate=lambda rec: (
            rec.get("status") == RUN_STATUS_SUCCEEDED and rec.get("score", 1.0) < 0.95
        ),
        dry_run=True,
    )
    assert len(would_delete) == 1

    deleted = analyzer.clean_results(
        statuses=(RUN_STATUS_FAILED,),
        dry_run=False,
        confirm=False,
    )
    assert len(deleted) == 1

    remaining = analyzer.to_dataframe(statuses=None)
    assert len(remaining) == 1
