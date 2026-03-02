# 0.3 到 0.4 迁移指南

本版本保持 `0.3` API 可用，以增量能力为主。

## 新增能力

1. 运行元数据：自动生成 `meta.json`，并在 `run.json` 中写入治理字段。
2. 指标流：支持 `metrics.jsonl`（step 级）与 `events.jsonl`（生命周期事件）。
3. 追踪器：支持 `track("jsonl"|"mlflow"|"wandb")`，其中 `mlflow/wandb` 为可选依赖。
4. Pipeline 治理接口：
   - `name(...)`
   - `group(...)`
   - `tags(...)`
   - `lineage(...)`
   - `retry(...)`
   - `random_search(...)`

## 兼容性说明

1. 旧 `exp_fn(ctx) -> dict | None` 契约不变。
2. 旧 run 目录（仅含 `config/run/metrics/artifacts`）仍可被 `ResultAnalyzer` 读取。
3. `RunContext` 新增字段：
   - `meta`
   - `log_metric(...)`

## 建议迁移步骤

1. 将版本升级到 `0.4.0`。
2. 在实验入口中补充治理字段（建议）：
   - `pipeline.name("...").group("...").tags({...})`
3. 在训练循环中替换日志打印为 `ctx.log_metric(...)`（建议）。
4. 若需要平台追踪，按需安装 extras：
   - `pip install "ztxexp[mlflow]"`
   - `pip install "ztxexp[wandb]"`

## 常见问题

1. 未安装 `mlflow/wandb` 但调用了对应追踪器
- 现象：运行时报 ImportError。
- 处理：安装对应 extras 或改用 `track("jsonl")`。

2. 并行模式下传入“实例化 tracker 对象”
- 现象：对象可能无法在子进程安全传输。
- 处理：并行模式优先使用字符串方式注册：
  - `track("jsonl")`
  - `track("mlflow", tracking_uri=..., experiment_name=...)`
