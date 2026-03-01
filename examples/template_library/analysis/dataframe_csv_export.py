"""DataFrame + CSV 导出。

场景说明：将 run 目录聚合为表格并导出 CSV。

复制后最少需要改动：
1. 将结果目录改为你的实际路径；
2. 调整字段名和筛选逻辑；
3. 将导出路径接入你的报告流程。
"""

from __future__ import annotations

import pandas as pd

from ztxexp import ResultAnalyzer

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 200)


def main() -> None:
    analyzer = ResultAnalyzer("./results_demo")
    df = analyzer.to_dataframe(statuses=("succeeded",))
    if df.empty:
        print("No successful runs found.")
        return

    print(df.head())
    analyzer.to_csv("./results_demo/summary.csv", sort_by=["run_id", "duration_sec"])


if __name__ == "__main__":
    main()
