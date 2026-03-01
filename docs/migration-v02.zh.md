# v0.2 迁移说明（中文）

## 破坏性变更

1. 结果目录协议从旧格式升级为 v2，仅支持：
   - `config.json`
   - `run.json`
   - `metrics.json`（可选）
   - `artifacts/`

2. 实验函数签名变更：
   - 旧：`exp_fn(args: argparse.Namespace)`
   - 新：`exp_fn(ctx: RunContext) -> dict | None`

3. 成功判定变更：
   - 旧：`_SUCCESS` 文件
   - 新：`run.json.status == "succeeded"`

4. `ResultAnalyzer.clean_results` 变更：
   - 旧：`incomplete_marker/filter_func`
   - 新：`statuses/predicate`

## 迁移步骤

1. 更新实验函数入参。

```python
# old
# def exp_fn(args):
#     lr = args.lr

# new
from ztxexp import RunContext

def exp_fn(ctx: RunContext):
    lr = ctx.config["lr"]
    return {"metric": 0.9}
```

2. 将业务产物写入 `ctx.run_dir / "artifacts"`。
3. 用 `ExperimentPipeline` 或新版 `ExpRunner` 驱动执行。
4. 旧结果目录请保留归档，不再被 v0.2 自动读取。

## 推荐替代写法

```python
summary = (
    ExperimentPipeline("./results", base_config={"seed": 42})
    .grid({"lr": [1e-3, 1e-2]})
    .exclude_completed()
    .run(exp_fn, mode="process_pool", workers=4)
)
```
