# ztxexp

`ztxexp` 是一个面向深度学习与大模型实验的抽象框架，围绕三件事设计：

1. 配置构建：可组合网格搜索、变体、修改器和过滤器。
2. 运行编排：顺序、并行和动态调度三种模式，统一写入 v2 结果协议。
3. 结果治理：DataFrame 聚合、透视导出、可编程清理。

## 文档导航

- 中文快速开始: [Quickstart (ZH)](quickstart.zh.md)
- 设计理念与抽象: [Concepts (ZH)](concepts.zh.md)
- 常见 recipes: [Recipes (ZH)](recipes.zh.md)
- v0.2 迁移说明: [Migration v0.2 (ZH)](migration-v02.zh.md)
- English overview: [Overview (EN)](overview.en.md)

## v0.2 关键变化

- 结果目录协议升级为 v2，统一 `config.json` / `run.json` / `metrics.json` / `artifacts/`。
- 实验函数签名升级为 `exp_fn(ctx: RunContext) -> dict | None`。
- 新增 `ExperimentPipeline`，提供一体化构建与运行入口。
- `dynamic` 模式保留，但标记为实验特性（experimental）。

## 快速跳转

- API 总览: [API Overview](api/index.md)
- 示例代码目录: `examples/`
- 发布与变更记录: `CHANGELOG.md`
