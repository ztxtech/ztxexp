# Quickstart (English)

## Install

```bash
pip install ztxexp
```

For torch-specific helpers:

```bash
pip install "ztxexp[torch]"
```

For Excel pivot export:

```bash
pip install "ztxexp[excel]"
```

## Minimal pipeline

```python
from ztxexp import ExperimentPipeline, RunContext


def exp_fn(ctx: RunContext):
    score = 1.0 - ctx.config["lr"]
    return {"score": round(score, 4)}


summary = (
    ExperimentPipeline("./results_demo", base_config={"seed": 42})
    .grid({"lr": [0.001, 0.01]})
    .variants([{"model": "tiny"}, {"model": "base"}])
    .exclude_completed()
    .run(exp_fn, mode="sequential")
)

print(summary)
```

## Analyze

```python
from ztxexp import ResultAnalyzer

analyzer = ResultAnalyzer("./results_demo")
df = analyzer.to_dataframe(statuses=("succeeded",))
print(df[["run_id", "model", "lr", "score"]])
```
