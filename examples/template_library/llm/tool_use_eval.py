"""Tool Use/Agent 调用评测。

场景说明：评估工具调用成功率、步骤数与响应时延。

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
    temperature = float(cfg.get("temperature", 0.0))
    time.sleep(0.05 + random.random() * 0.05)

    primary = 0.4 + random.random() * 0.5 - temperature * 0.1

    artifact = {
        "run_id": ctx.run_id,
        "config": cfg,
        "note": "replace with your real training/evaluation outputs",
    }
    artifact_path = Path(ctx.run_dir) / "artifacts" / "summary.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "tool_success_rate": round(primary, 4),
        "avg_steps": int(2 + random.random() * 6),
    }


if __name__ == "__main__":

    pipeline = (
        ExperimentPipeline(
            results_root="./results_templates/tool_use_eval",
            base_config={'seed': 42, 'task': 'tool_use_eval'},
        )
        .grid({'temperature': [0.0, 0.2], 'max_steps': [4, 8]})
        .variants([{'policy': 'react'}, {'policy': 'plan_execute'}])
        .exclude_completed()
    )
    summary = pipeline.run(
        exp_fn,
        mode="sequential",
        workers=1,
        cpu_threshold=80,
    )
    print(summary)
