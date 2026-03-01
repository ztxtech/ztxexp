from __future__ import annotations

import json
import time
from pathlib import Path

from ztxexp import RunContext


def llm_experiment_template(ctx: RunContext):
    """Template for LLM experiments.

    Replace `fake_score` with your real evaluation logic.
    """

    model_name = ctx.config["model_name"]
    prompt_set = ctx.config["prompt_set"]
    temperature = ctx.config.get("temperature", 0.0)

    # Simulate one run.
    time.sleep(0.2)
    fake_score = 0.65 + (0.05 if "instruct" in model_name else 0.02) - temperature * 0.1

    # Example: save generation artifacts.
    output = {
        "run_id": ctx.run_id,
        "model_name": model_name,
        "prompt_set": prompt_set,
        "temperature": temperature,
        "samples": [
            {"prompt": "Who are you?", "response": "I am a demo assistant."},
        ],
    }

    artifact_path = Path(ctx.run_dir) / "artifacts" / "samples.json"
    artifact_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    return {
        "eval_score": round(fake_score, 4),
        "token_per_sec": 38.5,
    }
