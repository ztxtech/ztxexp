"""LLM 安全评测模板。

场景说明：越狱/有害请求防护能力评估。

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
        "block_rate": round(primary, 4),
        "helpfulness": round(0.4 + random.random() * 0.55, 4),
    }


if __name__ == "__main__":

    pipeline = (
        ExperimentPipeline(
            results_root="./results_templates/safety_eval",
            base_config={'seed': 42, 'task': 'safety_eval'},
        )
        .grid({'temperature': [0.0, 0.3], 'guard_threshold': [0.4, 0.6]})
        .variants([{'guard': 'off'}, {'guard': 'on'}])
        .exclude_completed()
    )
    summary = pipeline.run(
        exp_fn,
        mode="sequential",
        workers=1,
        cpu_threshold=80,
    )
    print(summary)
