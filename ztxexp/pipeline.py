"""High-level experiment pipeline facade for ztxexp v0.2."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from ztxexp.manager import ExpManager
from ztxexp.runner import ExpRunner
from ztxexp.types import RunSummary


class ExperimentPipeline:
    """Facade API that combines config building and execution."""

    def __init__(
        self,
        results_root: str | Path,
        base_config: Mapping[str, Any] | None = None,
    ):
        self.results_root = Path(results_root)
        self._manager = ExpManager(base_config)
        self._exclude_completed = False

    def grid(self, param_grid: Mapping[str, Sequence[Any]]) -> "ExperimentPipeline":
        self._manager.grid(param_grid)
        return self

    def variants(self, variants: Sequence[Mapping[str, Any]]) -> "ExperimentPipeline":
        self._manager.variants(variants)
        return self

    def modify(self, fn):
        self._manager.modify(fn)
        return self

    def where(self, fn):
        self._manager.where(fn)
        return self

    def exclude_completed(self) -> "ExperimentPipeline":
        self._exclude_completed = True
        return self

    def build(self) -> list[dict[str, Any]]:
        if self._exclude_completed:
            self._manager.exclude_completed(self.results_root)
        return self._manager.build()

    def run(
        self,
        exp_fn,
        mode: str = "sequential",
        workers: int = 1,
        cpu_threshold: int = 80,
    ) -> RunSummary:
        configs = self.build()
        runner = ExpRunner(configs=configs, results_root=self.results_root)
        return runner.run(
            exp_function=exp_fn,
            mode=mode,
            workers=workers,
            cpu_threshold=cpu_threshold,
        )
