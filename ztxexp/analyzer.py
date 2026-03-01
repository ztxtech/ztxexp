"""结果分析与清理模块。

本模块面向 v2 运行目录协议，提供：
1. 记录聚合（to_records/to_dataframe）；
2. 导出（to_csv/to_pivot_excel）；
3. 清理（clean_results）。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable, Sequence

import pandas as pd

from ztxexp import utils
from ztxexp.constants import (
    RUN_SCHEMA_VERSION,
    RUN_STATUS_FAILED,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SKIPPED,
    RUN_STATUS_SUCCEEDED,
)

# 清理函数签名：输入单条扁平记录，返回是否删除。
RecordPredicate = Callable[[dict[str, Any]], bool]


class ResultAnalyzer:
    """实验结果分析器（仅支持 schema v2）。

    Args:
        results_path: 运行根目录。

    Raises:
        FileNotFoundError: 结果目录不存在时抛出。

    Examples:
        >>> analyzer = ResultAnalyzer("./results_demo")
        >>> df = analyzer.to_dataframe(statuses=("succeeded",))
    """

    def __init__(self, results_path: str | Path):
        self.results_path = Path(results_path)
        if not self.results_path.exists():
            raise FileNotFoundError(f"Results path does not exist: {self.results_path}")

    def to_records(
        self,
        statuses: Sequence[str] | None = (RUN_STATUS_SUCCEEDED,),
        metrics_filename: str = "metrics.json",
    ) -> list[dict[str, Any]]:
        """读取 run 目录并合并为记录列表。

        合并顺序：``config -> metrics -> run_meta``，后者覆盖前者同名键。

        Args:
            statuses: 允许状态集合；传 ``None`` 表示不过滤状态。
            metrics_filename: 指标文件名，默认 ``metrics.json``。

        Returns:
            list[dict[str, Any]]: 扁平化记录列表。

        Examples:
            >>> records = ResultAnalyzer("./results_demo").to_records(statuses=None)
            >>> isinstance(records, list)
            True
        """
        records: list[dict[str, Any]] = []
        target_statuses = set(statuses) if statuses is not None else None

        for run_dir in utils.get_subdirectories(self.results_path):
            record = self._load_record(run_dir, metrics_filename)
            if record is None:
                continue

            status = record.get("status")
            if target_statuses is not None and status not in target_statuses:
                continue

            records.append(record)

        return records

    def to_dataframe(
        self,
        statuses: Sequence[str] | None = (RUN_STATUS_SUCCEEDED,),
        metrics_filename: str = "metrics.json",
    ) -> pd.DataFrame:
        """将记录列表转为 DataFrame。

        Args:
            statuses: 状态过滤条件。
            metrics_filename: 指标文件名。

        Returns:
            pd.DataFrame: 聚合后的数据表；若无数据返回空 DataFrame。
        """
        records = self.to_records(statuses=statuses, metrics_filename=metrics_filename)
        if not records:
            return pd.DataFrame()
        return pd.DataFrame.from_records(records)

    def to_csv(
        self,
        output_path: str | Path,
        sort_by: Sequence[str] | None = None,
        statuses: Sequence[str] | None = (RUN_STATUS_SUCCEEDED,),
        metrics_filename: str = "metrics.json",
    ) -> pd.DataFrame:
        """导出 CSV，并返回导出所用 DataFrame。

        Args:
            output_path: CSV 输出路径。
            sort_by: 排序字段列表（仅会使用存在于列中的字段）。
            statuses: 状态过滤条件。
            metrics_filename: 指标文件名。

        Returns:
            pd.DataFrame: 导出用 DataFrame（可能为空）。
        """
        df = self.to_dataframe(statuses=statuses, metrics_filename=metrics_filename)
        if df.empty:
            print("No records found to export.")
            return df

        if sort_by:
            valid_keys = [key for key in sort_by if key in df.columns]
            if valid_keys:
                df = df.sort_values(by=valid_keys).reset_index(drop=True)

        df.to_csv(output_path, index=False)
        print(f"Saved CSV to {output_path}")
        return df

    def to_pivot_excel(
        self,
        output_path: str | Path,
        df: pd.DataFrame,
        index_cols: Sequence[str],
        column_cols: Sequence[str],
        value_cols: Sequence[str],
        add_ranking: bool = True,
        ranking_ascending: bool = False,
    ) -> None:
        """生成透视表并导出 Excel。

        Args:
            output_path: Excel 输出路径。
            df: 输入数据表。
            index_cols: 透视表行索引字段。
            column_cols: 透视表列索引字段。
            value_cols: 值字段。
            add_ranking: 是否附加名次标签（1st/2nd/3rd）。
            ranking_ascending: 排名方向。``False`` 通常用于“值越大越好”。

        Returns:
            None

        Notes:
            该功能依赖 ``openpyxl``。未安装时会给出提示并安全返回。
        """
        if df.empty:
            print("DataFrame is empty, cannot generate pivot table.")
            return

        try:
            pivot_df = df.pivot_table(index=index_cols, columns=column_cols, values=value_cols)
        except Exception as exc:
            print(f"Failed to create pivot table: {exc}")
            return

        if not add_ranking:
            try:
                pivot_df.to_excel(output_path)
            except ImportError:
                print(
                    "openpyxl is required for Excel export. "
                    "Install with: pip install openpyxl"
                )
                return
            print(f"Saved pivot table to {output_path}")
            return

        rank_df = pivot_df.rank(method="min", ascending=ranking_ascending)
        final_pivot = pivot_df.astype(str)
        rank_labels = {1.0: " (1st)", 2.0: " (2nd)", 3.0: " (3rd)"}

        for col in final_pivot.columns:
            for idx in final_pivot.index:
                value = pivot_df.at[idx, col]
                if pd.notna(value):
                    rank = rank_df.at[idx, col]
                    final_pivot.at[idx, col] = f"{value:.4f}{rank_labels.get(rank, '')}"
                else:
                    final_pivot.at[idx, col] = ""

        try:
            final_pivot.to_excel(output_path)
        except ImportError:
            print(
                "openpyxl is required for Excel export. "
                "Install with: pip install openpyxl"
            )
            return
        print(f"Saved ranked pivot table to {output_path}")

    def clean_results(
        self,
        statuses: Sequence[str] | None = (
            RUN_STATUS_FAILED,
            RUN_STATUS_RUNNING,
            RUN_STATUS_SKIPPED,
        ),
        predicate: RecordPredicate | None = None,
        dry_run: bool = True,
        metrics_filename: str = "metrics.json",
        confirm: bool = True,
    ) -> list[Path]:
        """清理匹配条件的 run 目录。

        删除条件采用 OR 逻辑：
        1) ``status in statuses``（当 statuses 非 None）；
        2) ``predicate(record) is True``（当 predicate 非空）。

        Args:
            statuses: 状态过滤集合；``None`` 表示不按状态筛选。
            predicate: 自定义删除规则。
            dry_run: 为 ``True`` 时只打印并返回候选，不执行删除。
            metrics_filename: 指标文件名。
            confirm: 非 dry-run 且为 ``True`` 时，删除前二次确认。

        Returns:
            list[Path]:
                - dry-run: 待删目录列表；
                - 非 dry-run: 实际删除成功的目录列表。

        Examples:
            >>> analyzer = ResultAnalyzer("./results_demo")
            >>> analyzer.clean_results(statuses=("failed",), dry_run=True)
        """
        target_statuses = set(statuses) if statuses is not None else None
        to_delete: list[Path] = []

        for run_dir in utils.get_subdirectories(self.results_path):
            record = self._load_record(run_dir, metrics_filename)
            if record is None:
                continue

            should_delete = False
            if target_statuses is not None and record.get("status") in target_statuses:
                should_delete = True
            if predicate and predicate(record):
                should_delete = True

            if should_delete:
                to_delete.append(run_dir)

        if not to_delete:
            print("No folders matched cleanup criteria.")
            return []

        print(f"Found {len(to_delete)} folders to delete.")
        for run_dir in to_delete:
            print(f"  - {run_dir.name}")

        if dry_run:
            print("Dry run enabled. Nothing was deleted.")
            return to_delete

        if confirm:
            answer = input(f"Delete these {len(to_delete)} folders permanently? (yes/no): ")
            if answer.strip().lower() != "yes":
                print("Deletion canceled.")
                return []

        deleted: list[Path] = []
        for run_dir in to_delete:
            try:
                shutil.rmtree(run_dir)
                deleted.append(run_dir)
            except Exception as exc:  # pragma: no cover
                print(f"Failed to delete {run_dir}: {exc}")

        print(f"Deleted {len(deleted)} folders.")
        return deleted

    def _load_record(self, run_dir: Path, metrics_filename: str) -> dict[str, Any] | None:
        """从单个 run 目录加载扁平记录。

        Args:
            run_dir: 单个 run 目录。
            metrics_filename: 指标文件名。

        Returns:
            dict[str, Any] | None: 合并记录；若目录不符合 v2 协议则返回 None。
        """
        run_meta = utils.load_json(run_dir / "run.json")
        if not run_meta:
            return None
        if run_meta.get("schema_version") != RUN_SCHEMA_VERSION:
            return None

        config = utils.load_json(run_dir / "config.json") or {}
        if not isinstance(config, dict):
            return None

        metrics = utils.load_json(run_dir / metrics_filename) or {}
        if not isinstance(metrics, dict):
            metrics = {}

        record: dict[str, Any] = {}
        record.update(config)
        record.update(metrics)
        record.update(run_meta)
        record["run_dir"] = str(run_dir.resolve())
        return record
