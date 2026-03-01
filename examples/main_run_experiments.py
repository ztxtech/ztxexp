from __future__ import annotations

from parallel_run import experiment_fn

from ztxexp import ExperimentPipeline

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
