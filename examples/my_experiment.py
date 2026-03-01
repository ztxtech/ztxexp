from __future__ import annotations

import random
import time

from ztxexp import RunContext


def experiment_entrypoint(ctx: RunContext):
    """Demo experiment function using v0.2 RunContext contract."""
    lr = ctx.config["lr"]
    model = ctx.config["model"]

    if lr > 0.05:
        time.sleep(0.2)
        raise ValueError(f"Learning rate {lr} is too high (demo failure).")

    time.sleep(0.4 if model == "base" else 0.2)
    accuracy = 0.9 - lr + random.random() * 0.03

    return {
        "accuracy": round(accuracy, 4),
        "loss": round((1 - accuracy) * 2, 4),
    }
