"""实验流水线统一入口。

``ExperimentPipeline`` 将配置构建与执行调度串成一个链式 API，适合
大多数实验脚本快速落地。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ztxexp.manager import ExpManager
from ztxexp.runner import ExpRunner
from ztxexp.types import RunContext, RunSummary


class ExperimentPipeline:
    """实验流水线 Facade。

    设计目标：
    1. 减少样板代码；
    2. 将管理与执行组合为统一入口；
    3. 保留底层 ``ExpManager`` / ``ExpRunner`` 的可控性。

    Args:
        results_root: 运行产物根目录。
        base_config: 基础配置字典，后续 grid/variants 将基于它扩展。

    Examples:
        >>> pipeline = (
        ...     ExperimentPipeline("./results", base_config={"seed": 42})
        ...     .grid({"lr": [1e-3, 1e-2]})
        ...     .variants([{"model": "tiny"}, {"model": "base"}])
        ... )
        >>> configs = pipeline.build()
        >>> len(configs)
        4
    """

    def __init__(
        self,
        results_root: str | Path,
        base_config: Mapping[str, Any] | None = None,
    ):
        self.results_root = Path(results_root)
        self._manager = ExpManager(base_config)
        self._exclude_completed = False

    def grid(self, param_grid: Mapping[str, Sequence[Any]]) -> "ExperimentPipeline":
        """添加网格参数空间。

        Args:
            param_grid: 参数网格，例如 ``{"lr": [1e-3, 1e-2]}``。

        Returns:
            ExperimentPipeline: 返回自身以支持链式调用。
        """
        self._manager.grid(param_grid)
        return self

    def variants(self, variants: Sequence[Mapping[str, Any]]) -> "ExperimentPipeline":
        """添加独立变体空间。

        Args:
            variants: 变体列表，每个元素是一个配置片段字典。

        Returns:
            ExperimentPipeline: 返回自身以支持链式调用。

        Examples:
            >>> pipeline.variants([{"model": "tiny"}, {"model": "base"}])
        """
        self._manager.variants(variants)
        return self

    def modify(self, fn: Callable[[dict[str, Any]], dict[str, Any] | None]) -> "ExperimentPipeline":
        """注册配置修改函数。

        Args:
            fn: 配置修改器。可原地修改并返回 ``None``，也可返回新字典。

        Returns:
            ExperimentPipeline: 返回自身以支持链式调用。
        """
        self._manager.modify(fn)
        return self

    def where(self, fn: Callable[[dict[str, Any]], bool]) -> "ExperimentPipeline":
        """注册配置过滤函数。

        Args:
            fn: 谓词函数。返回 ``True`` 表示保留配置。

        Returns:
            ExperimentPipeline: 返回自身以支持链式调用。
        """
        self._manager.where(fn)
        return self

    def exclude_completed(self) -> "ExperimentPipeline":
        """启用“排除已完成实验”逻辑。

        Returns:
            ExperimentPipeline: 返回自身以支持链式调用。
        """
        self._exclude_completed = True
        return self

    def build(self) -> list[dict[str, Any]]:
        """构建最终配置列表。

        Returns:
            list[dict[str, Any]]: 构建完成的配置字典列表。
        """
        if self._exclude_completed:
            self._manager.exclude_completed(self.results_root)
        return self._manager.build()

    def run(
        self,
        exp_fn: Callable[[RunContext], dict[str, Any] | None],
        mode: str = "sequential",
        workers: int = 1,
        cpu_threshold: int = 80,
    ) -> RunSummary:
        """构建配置并执行实验。

        Args:
            exp_fn: 单次实验函数，签名为 ``exp_fn(ctx: RunContext)``。
            mode: 执行模式，支持 ``sequential`` / ``process_pool`` /
                ``joblib`` / ``dynamic``。
            workers: 并行 worker 数量。
            cpu_threshold: ``dynamic`` 模式下的 CPU 提交阈值。

        Returns:
            RunSummary: 批量执行汇总信息。

        Examples:
            >>> def exp_fn(ctx: RunContext):
            ...     return {"score": 1.0}
            >>> summary = ExperimentPipeline("./results").run(exp_fn)
            >>> summary.total >= 0
            True
        """
        configs = self.build()
        runner = ExpRunner(configs=configs, results_root=self.results_root)
        return runner.run(
            exp_function=exp_fn,
            mode=mode,
            workers=workers,
            cpu_threshold=cpu_threshold,
        )
