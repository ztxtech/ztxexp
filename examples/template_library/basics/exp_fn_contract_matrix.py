"""`exp_fn` 契约矩阵模板。

场景说明：
1. 用一个模板同时演示 `exp_fn` 的四种关键结果路径：返回 dict、返回 None、SkipRun、异常失败。
2. 便于团队统一“返回什么、写到哪里、如何判定状态”的约定。

输入配置字段：
- `scenario`：
  - `return_metrics`：返回最终指标字典，触发 `metrics.json`。
  - `stream_only`：仅写 step 指标流并返回 `None`。
  - `skip`：主动跳过（`SkipRun`），run 状态为 `skipped`。
  - `fail`：抛出异常，run 状态为 `failed` 并生成 `error.log`。
- `lr`：示例超参数（可选）。

输出产物差异（由框架协议决定）：
- 所有场景都会有：`config.json`、`run.json`、`meta.json`、`events.jsonl`、`artifacts/`。
- `return_metrics` 会额外写入：`metrics.json`。
- `stream_only` 会写入：`metrics.jsonl`，通常没有 `metrics.json`。
- `fail` 会写入：`error.log`。

复制后最少改动：
1. 把 `exp_fn` 中伪指标替换为真实训练/评测逻辑。
2. 保留 `scenario` 分支用于本地自测，或改成你的业务分支条件。
3. 将你的模型、样本、报告统一写入 `ctx.run_dir / "artifacts"`。
"""

from __future__ import annotations

import json
from pathlib import Path

from ztxexp import ExperimentPipeline, RunContext, SkipRun


def exp_fn(ctx: RunContext) -> dict[str, float] | None:
    """演示 `exp_fn` 契约的四种典型分支。"""
    scenario = str(ctx.config.get("scenario", "return_metrics"))
    lr = float(ctx.config.get("lr", 0.001))

    artifact_payload = {
        "run_id": ctx.run_id,
        "scenario": scenario,
        "config": ctx.config,
        "note": "replace with your real experiment artifacts",
    }
    artifact_path = Path(ctx.run_dir) / "artifacts" / f"{scenario}.json"
    artifact_path.write_text(
        json.dumps(artifact_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if scenario == "return_metrics":
        ctx.log_metric(step=1, metrics={"loss": 0.83}, split="train", phase="fit")
        return {
            "score": round(1.0 - lr, 4),
            "best_val_loss": 0.71,
        }

    if scenario == "stream_only":
        ctx.log_metric(step=1, metrics={"loss": 0.92}, split="train", phase="fit")
        ctx.log_metric(step=2, metrics={"loss": 0.78}, split="train", phase="fit")
        return None

    if scenario == "skip":
        raise SkipRun("Scenario skip: this config should be skipped by design.")

    if scenario == "fail":
        raise RuntimeError("Scenario fail: intentional failure for contract demonstration.")

    raise ValueError(f"Unknown scenario: {scenario}")


if __name__ == "__main__":
    pipeline = (
        ExperimentPipeline(
            results_root="./results_templates/exp_fn_contract_matrix",
            base_config={"seed": 42, "task": "exp_fn_contract_matrix"},
        )
        .variants(
            [
                {"scenario": "return_metrics", "lr": 0.001},
                {"scenario": "stream_only", "lr": 0.005},
                {"scenario": "skip", "lr": 0.01},
                {"scenario": "fail", "lr": 0.02},
            ]
        )
    )

    summary = pipeline.run(exp_fn, mode="sequential")
    print(summary)
