"""清理策略模板。

场景说明：按状态和指标组合清理历史结果目录。

复制后最少需要改动：
1. 将结果目录改为你的实际路径；
2. 调整字段名和筛选逻辑；
3. 将导出路径接入你的报告流程。
"""

from __future__ import annotations

from ztxexp import ResultAnalyzer


def main() -> None:
    analyzer = ResultAnalyzer("./results_demo")

    print("Dry-run: clean failed/skipped/running")
    analyzer.clean_results(dry_run=True)

    print("Dry-run: clean low score succeeded runs")
    analyzer.clean_results(
        statuses=None,
        predicate=lambda rec: rec.get("status") == "succeeded" and rec.get("score", 1.0) < 0.8,
        dry_run=True,
    )


if __name__ == "__main__":
    main()
