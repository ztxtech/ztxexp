from __future__ import annotations

from ztxexp import ExpManager
from ztxexp.constants import RUN_SCHEMA_VERSION, RUN_STATUS_FAILED, RUN_STATUS_SUCCEEDED
from ztxexp.utils import create_dir, save_json


def _write_run(root, name, status, config):
    run_dir = root / name
    create_dir(run_dir)
    save_json(config, run_dir / "config.json")
    save_json(
        {
            "schema_version": RUN_SCHEMA_VERSION,
            "run_id": name,
            "status": status,
            "started_at": "2026-03-01T00:00:00+00:00",
            "finished_at": "2026-03-01T00:00:01+00:00",
            "duration_sec": 1.0,
            "error_type": None,
            "error_message": None,
        },
        run_dir / "run.json",
    )


def test_grid_variants_modify_where_pipeline():
    manager = (
        ExpManager({"seed": 1})
        .grid({"lr": [0.001, 0.01], "batch_size": [16, 32]})
        .variants([{"model": "tiny"}, {"model": "base"}])
        .modify(lambda cfg: {**cfg, "tag": f"{cfg['model']}-{cfg['batch_size']}"})
        .where(lambda cfg: not (cfg["model"] == "base" and cfg["batch_size"] == 16))
    )

    configs = manager.build()

    # 2x2 grid * 2 variants = 8, one filtered branch for each lr => 6
    assert len(configs) == 6
    assert all("tag" in cfg for cfg in configs)


def test_exclude_completed_only_filters_succeeded(tmp_path):
    _write_run(tmp_path, "run_ok", RUN_STATUS_SUCCEEDED, {"lr": 0.001, "model": "tiny"})
    _write_run(tmp_path, "run_fail", RUN_STATUS_FAILED, {"lr": 0.01, "model": "base"})

    configs = (
        ExpManager()
        .variants(
            [
                {"lr": 0.001, "model": "tiny"},
                {"lr": 0.01, "model": "base"},
            ]
        )
        .exclude_completed(tmp_path)
        .build()
    )

    assert configs == [{"lr": 0.01, "model": "base"}]


def test_config_equality_requires_same_keyset(tmp_path):
    # completed config intentionally misses one key.
    _write_run(tmp_path, "run_ok", RUN_STATUS_SUCCEEDED, {"lr": 0.001})

    configs = (
        ExpManager()
        .variants([{"lr": 0.001, "model": "tiny"}])
        .exclude_completed(tmp_path)
        .build()
    )

    assert configs == [{"lr": 0.001, "model": "tiny"}]


def test_random_search_builds_expected_trials():
    manager = ExpManager({"seed": 1}).random_search(
        {
            "lr": [0.001, 0.01],
            "model": ["tiny", "base"],
        },
        n_trials=5,
        seed=123,
    )
    configs = manager.build()

    assert len(configs) == 5
    assert all(cfg["lr"] in {0.001, 0.01} for cfg in configs)
    assert all(cfg["model"] in {"tiny", "base"} for cfg in configs)
    assert all(cfg["seed"] == 1 for cfg in configs)
