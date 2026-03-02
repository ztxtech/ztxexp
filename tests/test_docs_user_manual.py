from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_user_manual_contains_exp_fn_contract_sections():
    manual_path = ROOT / "docs_src" / "user-manual.zh.md"
    assert manual_path.exists()

    content = manual_path.read_text(encoding="utf-8")
    required_keywords = [
        "exp_fn(ctx: RunContext) -> dict | None",
        "返回值与状态矩阵",
        "产物协议矩阵",
        "SkipRun",
        "ctx.log_metric",
        "metrics.json",
        "metrics.jsonl",
        "error.log",
    ]
    for keyword in required_keywords:
        assert keyword in content
