from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path

from ztxexp import ExpRunner, RunContext, RunMetadata, utils

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = ROOT / "examples" / "template_library"


def _load_module(path: Path):
    module_name = f"template_{path.stem}_{uuid.uuid4().hex[:8]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_ctx(tmp_path: Path, config: dict[str, object]) -> RunContext:
    run_dir = tmp_path / f"run_{uuid.uuid4().hex[:8]}"
    utils.create_dir(run_dir / "artifacts")
    logger = utils.setup_logger(
        f"template.test.{uuid.uuid4().hex[:8]}",
        run_dir / "run.log",
    )
    return RunContext(
        run_id=run_dir.name,
        run_dir=run_dir,
        config=config,
        logger=logger,
        meta=RunMetadata(experiment_name="template_smoke"),
        _metrics_jsonl_path=run_dir / "metrics.jsonl",
    )


def _close_ctx_logger(ctx: RunContext) -> None:
    for handler in list(ctx.logger.handlers):
        handler.close()
        ctx.logger.removeHandler(handler)


def test_template_catalog_exists():
    assert (TEMPLATE_ROOT / "README.md").exists()


def test_template_smoke_run_categories(tmp_path):
    category_defaults = {
        "basics": {"lr": 0.001, "model": "tiny", "seed": 42},
        "parallel": {"lr": 0.001, "model": "tiny", "seed": 42},
        "ml": {"lr": 0.001, "model": "mlp", "seed": 42},
        "llm": {"temperature": 0.1, "top_p": 0.9, "seed": 42},
        "ops": {"lr": 0.001, "model": "tiny", "seed": 42},
    }

    for category, default_cfg in category_defaults.items():
        files = sorted((TEMPLATE_ROOT / category).glob("*.py"))
        assert len(files) >= 2
        for path in files[:2]:
            module = _load_module(path)
            assert hasattr(module, "exp_fn")

            ctx = _make_ctx(tmp_path, dict(default_cfg))
            result = module.exp_fn(ctx)
            assert result is None or isinstance(result, dict)
            assert (ctx.run_dir / "artifacts").exists()
            _close_ctx_logger(ctx)


def test_template_smoke_analysis_category(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # 先生成最小结果目录，供分析模板读取。
    ExpRunner(configs=[{"lr": 0.001, "model": "tiny"}], results_root="./results_demo").run(
        lambda ctx: {"score": 0.9},
        mode="sequential",
    )

    for name in ["dataframe_csv_export.py", "cleanup_policy.py"]:
        path = TEMPLATE_ROOT / "analysis" / name
        module = _load_module(path)
        assert hasattr(module, "main")
        module.main()
