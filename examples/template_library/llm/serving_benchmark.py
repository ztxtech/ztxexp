"""LLM 服务压测模板。

场景说明：不同并发、batch 规模下的吞吐与延迟对比。

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
    concurrency = float(cfg.get("concurrency", 1))
    time.sleep(0.05 + random.random() * 0.05)

    primary = 50 + random.random() * 20 + concurrency * 2

    artifact = {
        "run_id": ctx.run_id,
        "config": cfg,
        "note": "replace with your real training/evaluation outputs",
    }
    artifact_path = Path(ctx.run_dir) / "artifacts" / "summary.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "throughput": round(primary, 4),
        "p95_latency": round(200 + random.random() * 200, 2),
    }


if __name__ == "__main__":

    pipeline = (
        ExperimentPipeline(
            results_root="./results_templates/serving_benchmark",
            base_config={'seed': 42, 'task': 'serving_benchmark'},
        )
        .grid({'concurrency': [1, 4, 8], 'batch_size': [1, 4]})
        .variants([{'engine': 'vllm'}, {'engine': 'tgi'}])
        .exclude_completed()
    )
    summary = pipeline.run(
        exp_fn,
        mode="process_pool",
        workers=2,
        cpu_threshold=80,
    )
    print(summary)
