"""RAG 检索增强评测。

场景说明：不同检索策略/检索深度下的答案质量对比。

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

    primary = 0.5 + random.random() * 0.45 - temperature * 0.1

    artifact = {
        "run_id": ctx.run_id,
        "config": cfg,
        "note": "replace with your real training/evaluation outputs",
    }
    artifact_path = Path(ctx.run_dir) / "artifacts" / "summary.json"
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "answer_f1": round(primary, 4),
        "context_recall": round(0.4 + random.random() * 0.55, 4),
    }


if __name__ == "__main__":

    pipeline = (
        ExperimentPipeline(
            results_root="./results_templates/rag_eval",
            base_config={'seed': 42, 'task': 'rag_eval'},
        )
        .grid({'top_k': [3, 5, 10], 'temperature': [0.0, 0.2]})
        .variants([{'retriever': 'bm25'}, {'retriever': 'dense'}])
        .exclude_completed()
    )
    summary = pipeline.run(
        exp_fn,
        mode="sequential",
        workers=1,
        cpu_threshold=80,
    )
    print(summary)
