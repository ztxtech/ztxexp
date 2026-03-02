---
name: ztx-exp-manager
description: Manage ML/LLM experiment workflows with ztxexp. Use when the agent needs to build parameter configurations, run experiments, validate run artifacts, analyze results, or troubleshoot failed runs.
---

# ztx-exp-manager Skill（中文）

## 核心规则

1. 优先使用 `ExperimentPipeline` 组织实验，不手写零散调度脚本。
2. 实验函数契约固定为：`exp_fn(ctx: RunContext) -> dict | None`。
3. 成功判定必须使用：`run.json.status == "succeeded"`。
4. 产物分工：
   - 最终指标：`return dict` -> `metrics.json`
   - 过程指标：`ctx.log_metric(...)` -> `metrics.jsonl`
   - 业务文件：写入 `artifacts/`

## 常用流程

1. 先用 `grid/variants/random_search` 构建配置。
2. 再执行 `pipeline.run(exp_fn, mode=...)`。
3. 用 `ResultAnalyzer` 聚合、导出和清理。

## 常用命令

- `pip install -U ztxexp`
- `ztxexp init-vibe`
- `python -m pytest`

## 排障清单

1. 先看 `run.json.status`。
2. 失败时查看 `error.log`。
3. 曲线缺失时检查 `ctx.log_metric(...)` 是否调用。

---

# ztx-exp-manager Skill (English)

## Core Rules

1. Prefer `ExperimentPipeline` for workflow orchestration.
2. Keep experiment contract: `exp_fn(ctx: RunContext) -> dict | None`.
3. Determine success strictly by `run.json.status == "succeeded"`.
4. Artifact responsibilities:
   - Final metrics: `return dict` -> `metrics.json`
   - Step metrics: `ctx.log_metric(...)` -> `metrics.jsonl`
   - Business outputs: write into `artifacts/`

## Typical Workflow

1. Build configs via `grid/variants/random_search`.
2. Execute with `pipeline.run(exp_fn, mode=...)`.
3. Aggregate and clean results using `ResultAnalyzer`.

## Common Commands

- `pip install -U ztxexp`
- `ztxexp init-vibe`
- `python -m pytest`

## Troubleshooting

1. Check `run.json.status` first.
2. Read `error.log` on failure.
3. Verify `ctx.log_metric(...)` for missing curves.
