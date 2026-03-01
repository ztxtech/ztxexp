"""管理器与执行器解耦。

场景说明：当你需要先构建配置再交给不同 runner 时使用。

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

from ztxexp import ExpManager, ExpRunner, RunContext


def exp_fn(ctx: RunContext):
    """单次实验函数模板。"""
    cfg = ctx.config
    lr = float(cfg.get("lr", 0.001))
    time.sleep(0.05 + random.random() * 0.05)

    primary = 0.6 + random.random() * 0.35 - lr * 0.2

    artifact = {
        "run_id": ctx.run_id,
        "config": cfg,
        "note": "replace with your real training/evaluation outputs",
    }
    artifact_path = Path(ctx.run_dir) / "artifacts" / "summary.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "score": round(primary, 4),
        "latency_ms": round(200 + random.random() * 200, 2),
    }


if __name__ == "__main__":

    manager = (
        ExpManager(base_config={'seed': 42, 'task': 'manager_runner_split'})
        .grid({'lr': [0.001, 0.01]})
        .variants([{'model': 'tiny'}, {'model': 'base'}])
        .exclude_completed("./results_templates/manager_runner_split")
    )
    configs = manager.build()
    runner = ExpRunner(configs=configs, results_root="./results_templates/manager_runner_split")
    summary = runner.run(exp_fn, mode="sequential", workers=1)
    print(summary)
