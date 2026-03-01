"""排行榜对比模板。

场景说明：快速生成 Top-K 配置列表，便于版本评审。

复制后最少需要改动：
1. 将结果目录改为你的实际路径；
2. 调整字段名和筛选逻辑；
3. 将导出路径接入你的报告流程。
"""

from __future__ import annotations

import pandas as pd

from ztxexp import ResultAnalyzer


def main() -> None:
    analyzer = ResultAnalyzer("./results_demo")
    df = analyzer.to_dataframe(statuses=("succeeded",))
    if df.empty:
        print("No successful runs found.")
        return

    metric = "score" if "score" in df.columns else None
    if metric is None:
        print("No score-like metric found in records.")
        return

    leaderboard = df.sort_values(metric, ascending=False).head(10)
    cols = [
        c
        for c in ["run_id", "model", "lr", metric, "duration_sec"]
        if c in leaderboard.columns
    ]
    pd.set_option("display.max_columns", None)
    print(leaderboard[cols])


if __name__ == "__main__":
    main()
