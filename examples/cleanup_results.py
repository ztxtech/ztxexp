from __future__ import annotations

from ztxexp import ResultAnalyzer


def main() -> None:
    analyzer = ResultAnalyzer("./results_demo")

    print("Scenario 1: clean failed/skipped/running runs (dry-run)")
    analyzer.clean_results(dry_run=True)

    print("\nScenario 2: clean low-score succeeded runs (dry-run)")
    analyzer.clean_results(
        statuses=None,
        predicate=lambda rec: rec.get("status") == "succeeded" and rec.get("score", 1.0) < 0.85,
        dry_run=True,
    )


if __name__ == "__main__":
    main()
