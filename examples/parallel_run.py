from __future__ import annotations

import random
import time

from ztxexp import ExperimentPipeline, RunContext


def experiment_fn(ctx: RunContext):
    lr = ctx.config["lr"]
    model = ctx.config["model"]

    if lr > 0.05:
        raise ValueError(f"Learning rate {lr} is intentionally marked invalid for demo.")

    time.sleep(0.3 if model == "tiny" else 0.6)

    score = 0.9 - lr + random.random() * 0.03
    return {
        "score": round(score, 4),
        "latency_ms": 300 if model == "tiny" else 600,
    }


if __name__ == "__main__":
    pipeline = (
        ExperimentPipeline(
            results_root="./results_demo",
            base_config={"seed": 42, "dataset": "toy"},
        )
        .grid({"lr": [0.001, 0.01, 0.1]})
        .variants([{"model": "tiny"}, {"model": "base"}])
        .exclude_completed()
    )

    summary = pipeline.run(experiment_fn, mode="process_pool", workers=4)
    print(summary)
