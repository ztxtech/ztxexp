# Concepts（中文）

## 设计目标

- 面向实验迭代，而不是单次脚本执行。
- 把配置、运行、结果三个阶段拆开，降低耦合。
- 强制统一 run 产物协议，减少后处理脚本碎片化。

## 三层抽象

1. `ExpManager`
负责构建配置集合：`grid -> variants -> modify -> where -> exclude_completed`。

2. `ExpRunner`
负责调度与执行：`sequential` / `process_pool` / `joblib` / `dynamic`。

3. `ResultAnalyzer`
负责结果聚合和目录治理。

## 统一入口

`ExperimentPipeline` 是推荐入口，适合大多数项目：

- 减少样板代码。
- 内置 completed 过滤。
- 直接返回 `RunSummary`。

## v2 结果协议

每个 run 是一个独立目录，核心文件：

- `config.json`: 运行时使用的最终配置。
- `run.json`: 状态机元信息（`running/succeeded/failed/skipped`）。
- `metrics.json`: 实验函数返回的结构化指标（可选）。
- `artifacts/`: 模型权重、图表、日志等业务产物。

## 为什么废弃 `_SUCCESS`

`_SUCCESS` 只能表达“是否成功”，无法表达失败原因、耗时和运行状态。
`run.json` 能提供更完整、可扩展的治理能力。
