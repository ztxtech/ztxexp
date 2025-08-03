import shutil
from pathlib import Path

import pandas as pd

from ztxexp import utils
from ztxexp.runner import SUCCESS_MARKER  # Import the constant


class ResultAnalyzer:
    # ... (__init__ is unchanged) ...
    def __init__(self, results_path: str):
        self.results_path = Path(results_path)
        if not self.results_path.exists():
            raise FileNotFoundError(f"Results path does not exist: {self.results_path}")

    def to_dataframe(self, results_filename: str = 'results.json') -> pd.DataFrame:
        """
        Aggregates results into a pandas DataFrame.
        It now only considers folders with a _SUCCESS marker and merges
        'args.json' with a specified results file.

        Args:
            results_filename (str): The name of the file containing experiment
                                    metrics (e.g., 'results.json').
        """
        folders = utils.get_subdirectories(str(self.results_path))
        records = []

        print(f"Analyzing results... Looking for '{SUCCESS_MARKER}' and '{results_filename}'.")

        for folder in folders:
            # ONLY consider folders that have the success marker
            if not (folder / SUCCESS_MARKER).exists():
                continue

            args_path = folder / 'args.json'
            if args_path.exists():
                record = utils.load_json(str(args_path))
                if not record:
                    continue

                # Load results file and merge it into the record
                results_path = folder / results_filename
                if results_path.exists():
                    results_data = utils.load_json(str(results_path))
                    if results_data:
                        record.update(results_data)

                record['setting_path'] = str(folder.resolve())
                record['creation_time'] = utils.get_file_creation_time(args_path)
                records.append(record)

        if not records:
            print("No successfully completed experiments found.")
            return pd.DataFrame()

        return pd.DataFrame.from_records(records)

    def to_csv(self, output_path: str, sort_by: list[str] = None):
        """Saves the aggregated results to a CSV file."""

        df = self.to_dataframe()
        if df.empty:
            print("No results found to generate CSV.")
            return

        if sort_by:
            valid_sort_keys = [key for key in sort_by if key in df.columns]
            if valid_sort_keys:
                df = df.sort_values(by=valid_sort_keys).reset_index(drop=True)

        df.to_csv(output_path, index=False)
        print(f"Results saved to {output_path}")

    def to_pivot_excel(self, output_path: str, df: pd.DataFrame, index_cols: list[str], column_cols: list[str],
                       value_cols: list[str], add_ranking: bool = True):
        """Creates a pivot table from the results and saves it to an Excel file."""

        if df.empty:
            print("DataFrame is empty, cannot generate pivot table.")
            return

        try:
            pivot_df = df.pivot_table(
                index=index_cols,
                columns=column_cols,
                values=value_cols
            )
        except Exception as e:
            print(f"Could not create pivot table. Error: {e}")
            return

        if not add_ranking:
            pivot_df.to_excel(output_path)
            print(f"Pivot table saved to {output_path}")
            return

        rank_df = pivot_df.rank(method='min', ascending=True)
        final_pivot = pivot_df.astype(str)
        rank_labels = {1: ' (1st)', 2: ' (2nd)', 3: ' (3rd)'}

        for col in final_pivot.columns:
            for idx in final_pivot.index:
                value = pivot_df.at[idx, col]
                if pd.notna(value):
                    rank = rank_df.at[idx, col]
                    rank_label = rank_labels.get(rank, '')
                    final_pivot.at[idx, col] = f"{value:.4f}{rank_label}"
                else:
                    final_pivot.at[idx, col] = ""

        final_pivot.to_excel(output_path)
        print(f"Pivot table with ranking saved to {output_path}")

    def clean_results(self,
                      incomplete_marker: str = SUCCESS_MARKER,  # Default to the reliable marker
                      filter_func: callable = None,
                      dry_run: bool = True):
        """
        Deletes result folders based on specified criteria.

        Args:
            incomplete_marker (str, optional): A filename (e.g., 'metrics.npy' or 'final.pth')
                that marks an experiment as complete. Folders missing this file will be
                targeted for deletion.
            filter_func (callable, optional): A function that takes a configuration
                dictionary (from args.json) and returns True if the folder should be deleted.
            dry_run (bool): If True, only prints which folders would be deleted without
                actually deleting them. Set to False to perform deletion.
        """
        folders_to_delete = set()
        all_folders = utils.get_subdirectories(str(self.results_path))

        # 1. Identify folders based on criteria
        for folder in all_folders:
            # Criterion 1: Check for incomplete runs
            if incomplete_marker and not (folder / incomplete_marker).exists():
                folders_to_delete.add(folder)
                print(f"[INCOMPLETE] Marked for deletion: {folder.name} (missing '{incomplete_marker}')")
                continue  # Move to next folder once marked

            # Criterion 2: Apply custom filter function
            if filter_func:
                args_path = folder / 'args.json'
                if args_path.exists():
                    config = utils.load_json(str(args_path))
                    if config and filter_func(config):
                        folders_to_delete.add(folder)
                        print(f"[FILTER MATCH] Marked for deletion: {folder.name}")

        if not folders_to_delete:
            print("No folders matched the cleaning criteria.")
            return

        print("\n" + "=" * 50)
        print(f"Found {len(folders_to_delete)} folders to delete.")
        print("=" * 50)

        # 2. Perform deletion (or simulate if dry_run)
        if dry_run:
            print("\n[DRY RUN] The following folders would be deleted:")
            for folder in sorted(list(folders_to_delete)):
                print(f"  - {folder.name}")
            print("\nTo delete these folders, run this method with `dry_run=False`.")
        else:
            # Confirmation step for safety
            confirm = input(
                f"Are you sure you want to permanently delete these {len(folders_to_delete)} folders? (yes/no): ")
            if confirm.lower() == 'yes':
                print("Deleting folders...")
                for folder in folders_to_delete:
                    try:
                        shutil.rmtree(folder)
                        print(f"  - Deleted: {folder.name}")
                    except Exception as e:
                        print(f"  - Error deleting {folder.name}: {e}")
                print("Cleaning complete.")
            else:
                print("Deletion cancelled by user.")
