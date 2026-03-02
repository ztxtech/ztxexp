"""实验流水线统一入口。

``ExperimentPipeline`` 将配置构建与执行调度串成一个链式 API，适合
大多数实验脚本快速落地。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ztxexp.manager import ExpManager
from ztxexp.runner import ExpRunner
from ztxexp.tracking import Tracker
from ztxexp.types import RunContext, RunMetadata, RunSummary


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
        self._experiment_name: str | None = None
        self._group_name: str | None = None
        self._tags: dict[str, str] | list[str] | None = None
        self._parent_run_id: str | None = None
        self._retry_max_attempts = 1
        self._retry_on = ("Exception",)
        self._tracker_specs: list[dict[str, Any]] = []
        self._trackers: list[Tracker] = []

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

    def random_search(
        self,
        space: Mapping[str, Sequence[Any]],
        n_trials: int,
        seed: int = 42,
    ) -> "ExperimentPipeline":
        """添加随机搜索空间。"""
        self._manager.random_search(space=space, n_trials=n_trials, seed=seed)
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

    def name(self, experiment_name: str) -> "ExperimentPipeline":
        """设置实验名称。"""
        self._experiment_name = experiment_name
        return self

    def group(self, group_name: str) -> "ExperimentPipeline":
        """设置实验分组。"""
        self._group_name = group_name
        return self

    def tags(self, tags: dict[str, str] | list[str]) -> "ExperimentPipeline":
        """设置实验标签。"""
        self._tags = tags
        return self

    def lineage(self, parent_run_id: str | None) -> "ExperimentPipeline":
        """设置父 run ID。"""
        self._parent_run_id = parent_run_id
        return self

    def retry(
        self,
        max_attempts: int = 1,
        retry_on: tuple[str, ...] = ("Exception",),
    ) -> "ExperimentPipeline":
        """设置失败重试策略。"""
        self._retry_max_attempts = max(1, int(max_attempts))
        self._retry_on = retry_on
        return self

    def track(self, tracker: Tracker | str, **kwargs: Any) -> "ExperimentPipeline":
        """注册追踪器。

        Args:
            tracker: 追踪器实例或内置追踪器名（``jsonl/mlflow/wandb``）。
            **kwargs: 追踪器初始化参数（字符串模式下使用）。
        """
        if isinstance(tracker, str):
            self._tracker_specs.append({"type": tracker.lower(), "kwargs": dict(kwargs)})
            return self

        self._trackers.append(tracker)
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
        run_meta = RunMetadata(
            experiment_name=self._experiment_name,
            group=self._group_name,
            tags=self._tags,
            parent_run_id=self._parent_run_id,
        )

        has_jsonl_spec = any(spec.get("type") == "jsonl" for spec in self._tracker_specs)
        has_jsonl_instance = any(
            tracker.__class__.__name__ == "JsonlTracker" for tracker in self._trackers
        )
        if not has_jsonl_spec and not has_jsonl_instance:
            self._tracker_specs.append({"type": "jsonl", "kwargs": {}})

        return runner.run(
            exp_function=exp_fn,
            mode=mode,
            workers=workers,
            cpu_threshold=cpu_threshold,
            metadata=run_meta,
            max_attempts=self._retry_max_attempts,
            retry_on=self._retry_on,
            tracker_specs=self._tracker_specs,
            trackers=self._trackers,
        )
