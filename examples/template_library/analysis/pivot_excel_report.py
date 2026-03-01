"""透视表 Excel 报告。

场景说明：按模型/超参数维度输出可读的透视表报告。

复制后最少需要改动：
1. 将结果目录改为你的实际路径；
2. 调整字段名和筛选逻辑；
3. 将导出路径接入你的报告流程。
"""

from __future__ import annotations

from ztxexp import ResultAnalyzer


def main() -> None:
    analyzer = ResultAnalyzer("./results_demo")
    df = analyzer.to_dataframe(statuses=("succeeded",))
    if df.empty:
        print("No successful runs found.")
        return

    analyzer.to_pivot_excel(
        output_path="./results_demo/pivot_summary.xlsx",
        df=df,
        index_cols=["model"],
        column_cols=["lr"],
        value_cols=["score"],
        add_ranking=True,
        ranking_ascending=False,
    )


if __name__ == "__main__":
    main()
