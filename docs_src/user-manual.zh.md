# 用户手册（中文）

本手册面向**直接使用 ztxexp 开发实验**的用户，而不是仅查询 API 参数。  
如果你只想知道函数签名，请看 API 参考；如果你想知道一个实验应该怎么落地、产物怎么组织、失败如何排查，请按本手册执行。

## 1. 先理解 `exp_fn` 契约

`ztxexp` 的单次实验函数固定签名：

```python
def exp_fn(ctx: RunContext) -> dict | None:
    ...
```

### 1.1 `ctx` 里最关键的字段

- `ctx.run_id`：本次 run 的唯一 ID（通常也是目录名）。
- `ctx.run_dir`：本次 run 的目录路径。
- `ctx.config`：当前配置字典（已经是最终配置，不需要再从 argparse 解析）。
- `ctx.logger`：当前 run 专属日志器，写入 `run.log`。
- `ctx.meta`：运行元数据（实验名、分组、标签、种子、环境采集信息等）。

### 1.2 `ctx.log_metric(...)` 用于过程指标

当你希望记录 step 级曲线（例如每个 epoch 的 loss/acc）时，使用：

```python
ctx.log_metric(step=1, metrics={"loss": 0.92, "acc": 0.71}, split="train", phase="fit")
```

这会写入 `metrics.jsonl`（每行一个事件），并触发已注册 tracker 的 `on_metric` 回调。

## 2. 返回值与状态矩阵（决定 run 成败）

`exp_fn` 只允许返回 `dict | None`。不同返回/异常对应的行为如下：

| 场景 | 你在 `exp_fn` 中做什么 | run 状态 | 关键产物 |
| --- | --- | --- | --- |
| 最终指标返回 | `return {"score": 0.93}` | `succeeded` | `metrics.json` |
| 仅过程曲线 | `ctx.log_metric(...); return None` | `succeeded` | `metrics.jsonl`（无 `metrics.json`） |
| 主动跳过 | `raise SkipRun("reason")` | `skipped` | `run.json` + `events.jsonl`（skip 事件） |
| 业务异常 | 抛出异常（如 `RuntimeError`） | `failed` | `error.log` + `run.json.error_*` |
| 非法返回值 | `return 123` 等非 `dict|None` | `failed` | `error.log`（`TypeError`） |

### 2.1 关键判定规则

- 成功判定只看：`run.json.status == "succeeded"`。
- 不再使用旧版 `_SUCCESS` 文件。

## 3. 产物协议矩阵（该写什么、写到哪里）

每个 run 目录遵循 v2 协议，核心结构如下：

```text
<results_root>/<run_id>/
  config.json
  run.json
  meta.json
  metrics.json            # 可选
  metrics.jsonl           # 可选
  events.jsonl            # 可选
  artifacts/
  checkpoints/
  run.log
  error.log               # 失败时
```

| 产物 | 谁写入 | 何时出现 | 必选/可选 | 说明 |
| --- | --- | --- | --- | --- |
| `config.json` | 框架 | run 启动时 | 必选 | 当前 run 的最终配置快照。 |
| `run.json` | 框架 | 启动时创建，结束时回填 | 必选 | 状态机文件，含 `status/start/finish/error` 等。 |
| `meta.json` | 框架 | 启动时写入，可随重试更新 | 必选（v0.4+） | 复现与治理元数据。 |
| `metrics.json` | 框架 | `exp_fn` 返回 `dict` 时 | 可选 | 最终指标快照，适合排名/汇总。 |
| `metrics.jsonl` | 框架 | 调用 `ctx.log_metric` 后 | 可选 | step 级时间序列指标。 |
| `events.jsonl` | 框架 | run 生命周期中 | 可选 | `start/retry/skip/error/end` 事件流。 |
| `artifacts/` | 用户 + 框架创建目录 | run 启动时创建目录 | 必选目录 | 业务文件统一放这里（模型、图表、报告等）。 |
| `checkpoints/` | 用户 + 框架创建目录 | run 启动时创建目录 | 必选目录 | 断点恢复文件建议统一放这里。 |
| `error.log` | 框架 | run 失败时 | 可选 | 失败堆栈，优先排查入口。 |

## 4. 最终指标、过程指标、业务产物如何分工

- 最终指标（用于横向比较）：`return dict`，自动落到 `metrics.json`。
- 过程指标（用于画曲线和诊断）：`ctx.log_metric(...)`，落到 `metrics.jsonl`。
- 业务产物（模型、日志、图表、预测样本）：手动写入 `artifacts/`。
- checkpoint（恢复训练）：写入 `checkpoints/`。

推荐做法：

1. 在 `metrics.json` 只保留关键汇总指标（如 `best_val_f1`、`test_acc`）。
2. 在 `metrics.jsonl` 记录细粒度训练过程（每 step/epoch）。
3. 把大文件和中间物全部放在 `artifacts/` 或 `checkpoints/`，不要污染 run 根目录。

## 5. 用户开发流程（从 0 到可分析）

### 5.1 构建配置

使用 `ExperimentPipeline` 或 `ExpManager` 构建参数空间：

```python
from ztxexp import ExperimentPipeline

pipeline = (
    ExperimentPipeline("./results_demo", base_config={"seed": 42})
    .grid({"lr": [1e-3, 1e-2]})
    .variants([{"model": "tiny"}, {"model": "base"}])
    .exclude_completed()
)
```

### 5.2 编写 `exp_fn`

```python
from pathlib import Path
from ztxexp import RunContext


def exp_fn(ctx: RunContext) -> dict | None:
    lr = float(ctx.config["lr"])
    model = str(ctx.config["model"])

    # 过程指标
    ctx.log_metric(step=1, metrics={"loss": 0.8}, split="train", phase="fit")

    # 业务产物
    artifact = Path(ctx.run_dir) / "artifacts" / "summary.txt"
    artifact.write_text(f"run={ctx.run_id}, model={model}, lr={lr}\n", encoding="utf-8")

    # 最终指标
    return {"score": round(1.0 - lr, 4)}
```

### 5.3 选择执行模式

- `sequential`：先保证正确性，再扩并发。
- `process_pool`：CPU 密集任务优先考虑。
- `joblib`：需要与 joblib 生态兼容时使用。
- `dynamic`：实验特性，按 CPU 阈值动态提交。

### 5.4 分析与清理

```python
from ztxexp import ResultAnalyzer

analyzer = ResultAnalyzer("./results_demo")
df = analyzer.to_dataframe(statuses=("succeeded",))
curve_df = analyzer.to_curve_dataframe(metric_key="loss")
```

## 6. 调试与排错清单

1. 先看 `run.json.status`，再看 `error.log`。
2. 结果为空时检查：是否 `return dict`、是否被 `SkipRun`、是否被过滤条件排除。
3. 曲线缺失时检查：是否调用了 `ctx.log_metric`。
4. `exclude_completed` 异常时检查：历史目录是否是 v2 协议且成功状态是 `succeeded`。
5. 并行场景异常先切 `sequential` 复现，再回到并行模式。

## 7. 复制即改：建议优先使用这些模板

- 契约矩阵模板（本手册对应）：
  - `examples/template_library/basics/exp_fn_contract_matrix.py`
- 模板库入口：
  - [示例模板库导航](examples-lib/index.md)
  - [模板索引表](examples-lib/catalog.md)
  - [场景复制矩阵](examples-lib/matrix.md)

## 8. 与 API 参考的关系

- 用户手册（本页）：回答“如何用 ztxexp 开发完整实验”。
- API 参考：回答“某个类/函数的参数、返回值和签名是什么”。

建议阅读顺序：

1. 先看本手册完成第一个可运行实验；
2. 再按需跳转 API 页面查看细节参数。
