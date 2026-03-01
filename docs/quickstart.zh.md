# 快速开始（中文）

本页面给出一个 5 分钟可跑通的最小流程。

## 1. 安装

```bash
pip install ztxexp
```

如果你要使用 PyTorch 相关工具：

```bash
pip install "ztxexp[torch]"
```

如果你要导出 Excel 透视表：

```bash
pip install "ztxexp[excel]"
```

## 2. 最小实验脚本

```python
from ztxexp import ExperimentPipeline, RunContext


def train_once(ctx: RunContext):
    lr = ctx.config["lr"]
    model = ctx.config["model"]

    # 业务产物建议写到 artifacts 目录
    artifact = ctx.run_dir / "artifacts" / "note.txt"
    artifact.write_text(f"run={ctx.run_id}, model={model}, lr={lr}\n", encoding="utf-8")

    # 返回 dict 会被框架写入 metrics.json
    score = (1.0 - lr) + (0.05 if model == "tiny" else 0.02)
    return {"score": round(score, 4)}


pipeline = (
    ExperimentPipeline(results_root="./results_demo", base_config={"seed": 42})
    .grid({"lr": [0.001, 0.01]})
    .variants([
        {"model": "tiny"},
        {"model": "base"},
    ])
    .exclude_completed()
)

summary = pipeline.run(train_once, mode="sequential")
print(summary)
```

## 3. 查看结果

每个 run 会生成以下结构：

```text
results_demo/
  20260301_120102_ab12cd34/
    config.json
    run.json
    metrics.json
    artifacts/
    run.log
```

`run.json` 中的 `status` 是判定成功与失败的唯一标准。

## 4. 聚合分析

```python
from ztxexp import ResultAnalyzer

analyzer = ResultAnalyzer("./results_demo")
df = analyzer.to_dataframe(statuses=("succeeded",))
print(df[["run_id", "model", "lr", "score"]])
analyzer.to_csv("./results_demo/summary.csv", sort_by=["model", "lr"])
```

## 5. 清理失败实验

```python
from ztxexp import ResultAnalyzer

analyzer = ResultAnalyzer("./results_demo")
analyzer.clean_results(statuses=("failed", "skipped"), dry_run=True)
```
