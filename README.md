# ztxexp

[![PyPI version](https://badge.fury.io/py/ztxexp.svg)](https://badge.fury.io/py/ztxexp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/ztxexp.svg)](https://pypi.org/project/ztxexp)

`ztxexp` 是一个面向深度学习和大模型实验的抽象框架，目标是让实验迭代更快、更可复现。

## 问题

在真实项目里，实验常见痛点是：

- 参数空间大，配置组合容易失控。
- 并行执行后目录结构混乱，成功/失败难追溯。
- 结果聚合脚本碎片化，清理成本高。

## 方案

`ztxexp` 提供四个核心抽象：

1. `ExpManager`: 负责配置构建（`grid`、`variants`、`modify`、`where`）。
2. `ExpRunner`: 负责执行调度（`sequential` / `process_pool` / `joblib` / `dynamic`）。
3. `ResultAnalyzer`: 负责聚合与清理。
4. `ExperimentPipeline`: 一体化入口，适合绝大多数场景。

v0.2 统一了 run 产物协议（schema v2）：

- `config.json`
- `run.json`
- `metrics.json`（可选）
- `artifacts/`

> 成功判定规则：`run.json.status == "succeeded"`

## 5 分钟跑通

### 安装

```bash
pip install ztxexp
```

可选：启用 PyTorch 辅助工具。

```bash
pip install "ztxexp[torch]"
```

如果你要导出 Excel 透视表：

```bash
pip install "ztxexp[excel]"
```

### 最小示例

```python
from ztxexp import ExperimentPipeline, RunContext


def exp_fn(ctx: RunContext):
    lr = ctx.config["lr"]
    model = ctx.config["model"]

    # 业务产物统一放 artifacts 目录
    (ctx.run_dir / "artifacts" / "info.txt").write_text(
        f"run={ctx.run_id}, model={model}, lr={lr}\n",
        encoding="utf-8",
    )

    # 返回 dict 会自动写入 metrics.json
    return {"score": round((1.0 - lr) + (0.05 if model == "tiny" else 0.02), 4)}


summary = (
    ExperimentPipeline("./results_demo", base_config={"seed": 42})
    .grid({"lr": [0.001, 0.01]})
    .variants([{"model": "tiny"}, {"model": "base"}])
    .exclude_completed()
    .run(exp_fn, mode="sequential")
)

print(summary)
```

### 聚合结果

```python
from ztxexp import ResultAnalyzer

analyzer = ResultAnalyzer("./results_demo")
df = analyzer.to_dataframe(statuses=("succeeded",))
print(df[["run_id", "model", "lr", "score"]])
analyzer.to_csv("./results_demo/summary.csv", sort_by=["model", "lr"])
```

## 常见坑

1. 返回值不是 `dict | None`
会被判定为失败，并写入 `error.log`。

2. 仍按旧版 `_SUCCESS` 判断成功
v0.2 不再使用 `_SUCCESS`，以 `run.json` 为准。

3. 直接把大文件写在 run 根目录
建议统一放到 `artifacts/`，便于后续清理和归档。

4. `dynamic` 模式用于生产实时场景
`dynamic` 是实验特性（experimental），更适合离线批任务。

## API 导航

- 中文文档入口: [docs/index.md](docs/index.md)
- 快速开始: [docs/quickstart.zh.md](docs/quickstart.zh.md)
- 迁移说明: [docs/migration-v02.zh.md](docs/migration-v02.zh.md)
- English overview: [docs/overview.en.md](docs/overview.en.md)
- API 参考: [docs/api/index.md](docs/api/index.md)

## 贡献

欢迎提交 Issue 或 PR：

- Issues: https://github.com/ztxtech/ztxexp/issues
- Repository: https://github.com/ztxtech/ztxexp

## 许可证

MIT License
