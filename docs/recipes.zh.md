# Recipes（中文）

## Recipe 1: 组合网格和变体

```python
from ztxexp import ExpManager

manager = (
    ExpManager({"seed": 42})
    .grid({"lr": [1e-3, 1e-2], "batch_size": [16, 32]})
    .variants([
        {"model": "tiny"},
        {"model": "base", "layers": 12},
    ])
    .modify(lambda cfg: {**cfg, "tag": f"{cfg['model']}_bs{cfg['batch_size']}"})
    .where(lambda cfg: not (cfg["model"] == "base" and cfg["batch_size"] == 16))
)

configs = manager.build()
```

## Recipe 2: 只重跑失败实验

```python
from ztxexp import ResultAnalyzer

analyzer = ResultAnalyzer("./results_demo")
failed_df = analyzer.to_dataframe(statuses=("failed", "skipped"))
print(failed_df[["run_id", "status", "error_type"]])
```

## Recipe 3: 按指标清理结果目录

```python
from ztxexp import ResultAnalyzer

analyzer = ResultAnalyzer("./results_demo")

analyzer.clean_results(
    statuses=None,
    predicate=lambda rec: rec.get("status") == "succeeded" and rec.get("score", 0.0) < 0.8,
    dry_run=True,
)
```

## Recipe 4: Dynamic 模式

```python
summary = pipeline.run(exp_fn, mode="dynamic", workers=4, cpu_threshold=75)
```

注意：`dynamic` 是实验特性（experimental），适合吞吐优先的离线任务，不建议用于强实时场景。
