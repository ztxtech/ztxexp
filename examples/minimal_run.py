from __future__ import annotations

from ztxexp import ExperimentPipeline, RunContext


def experiment_fn(ctx: RunContext):
    lr = ctx.config["lr"]
    model = ctx.config["model"]

    note = ctx.run_dir / "artifacts" / "note.txt"
    note.write_text(f"run={ctx.run_id}, model={model}, lr={lr}\n", encoding="utf-8")

    score = (1.0 - lr) + (0.05 if model == "tiny" else 0.02)
    return {"score": round(score, 4)}


if __name__ == "__main__":
    pipeline = (
        ExperimentPipeline(results_root="./results_demo", base_config={"seed": 42})
        .grid({"lr": [0.001, 0.01]})
        .variants([{"model": "tiny"}, {"model": "base"}])
        .exclude_completed()
    )

    summary = pipeline.run(experiment_fn, mode="sequential")
    print(summary)
