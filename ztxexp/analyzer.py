"""Result analysis and cleanup for ztxexp v0.2 artifact format."""

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

RecordPredicate = Callable[[dict[str, Any]], bool]


class ResultAnalyzer:
    """Reads and manages experiment artifacts in the v2 run directory format."""

    def __init__(self, results_path: str | Path):
        self.results_path = Path(results_path)
        if not self.results_path.exists():
            raise FileNotFoundError(f"Results path does not exist: {self.results_path}")

    def to_records(
        self,
        statuses: Sequence[str] | None = (RUN_STATUS_SUCCEEDED,),
        metrics_filename: str = "metrics.json",
    ) -> list[dict[str, Any]]:
        """Loads run records by merging config/run metadata/metrics."""
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
        """Converts run records to DataFrame."""
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
        """Exports records to CSV and returns the DataFrame used for export."""
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
        """Creates and saves a pivot table from the input DataFrame."""
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
        """Deletes run folders that match status and/or custom predicate.

        A run folder is marked for deletion when:
        1) Its status is in `statuses` (if statuses is provided), or
        2) `predicate(record)` returns True.
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

        record = {}
        record.update(config)
        record.update(metrics)
        record.update(run_meta)
        record["run_dir"] = str(run_dir.resolve())
        return record
