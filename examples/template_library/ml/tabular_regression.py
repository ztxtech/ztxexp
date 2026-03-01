"""表格回归模板。

场景说明：回归任务的 RMSE/MAE 指标记录骨架。

复制后最少需要改动：
1. 将 `exp_fn` 中的伪指标逻辑替换为真实训练/评测代码；
2. 调整 `grid/variants` 到你的参数空间；
3. 将产物写入 `ctx.run_dir / "artifacts"`。
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

from ztxexp import ExperimentPipeline, RunContext


def exp_fn(ctx: RunContext):
    """单次实验函数模板。"""
    cfg = ctx.config
    lr = float(cfg.get("lr", 0.001))
    time.sleep(0.05 + random.random() * 0.05)

    primary = 0.2 + lr * 2.0 + random.random() * 0.05

    artifact = {
        "run_id": ctx.run_id,
        "config": cfg,
        "note": "replace with your real training/evaluation outputs",
    }
    artifact_path = Path(ctx.run_dir) / "artifacts" / "summary.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "rmse": round(primary, 4),
        "mae": round(0.4 + random.random() * 0.55, 4),
    }


if __name__ == "__main__":

    pipeline = (
        ExperimentPipeline(
            results_root="./results_templates/tabular_regression",
            base_config={'seed': 42, 'task': 'tabular_regression'},
        )
        .grid({'lr': [0.0005, 0.001], 'batch_size': [64, 128]})
        .variants([{'model': 'gbdt'}, {'model': 'mlp'}])
        .exclude_completed()
    )
    summary = pipeline.run(
        exp_fn,
        mode="process_pool",
        workers=2,
        cpu_threshold=80,
    )
    print(summary)
