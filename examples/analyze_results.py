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
    else:
        print(df[["run_id", "model", "lr", "score", "duration_sec"]])
        analyzer.to_csv(
            "./results_demo/summary.csv",
            sort_by=["model", "lr"],
            statuses=("succeeded",),
        )

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
