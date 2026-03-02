"""ztxexp 对外公开的运行时数据结构。"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import utils

if TYPE_CHECKING:  # pragma: no cover
    from ztxexp.tracking import Tracker


@dataclass(slots=True)
class RunMetadata:
    """运行元数据。

    用于描述一次 run 的治理与复现上下文。字段均为可选，框架会在运行时
    自动填充可采集部分（如 python 版本、平台、命令行等）。

    Attributes:
        experiment_name: 实验名称。
        group: 实验分组。
        tags: 标签（可为字典或字符串列表）。
        parent_run_id: 父 run ID（用于 lineage）。
        attempt: 当前尝试次数（重试时递增）。
        git_commit: 当前代码 commit。
        python_version: Python 版本。
        platform: 运行平台描述。
        hostname: 主机名。
        started_cmd: 启动命令。
        dataset_version: 数据版本标识。
        seed: 随机种子。
        extras: 其它扩展元数据。
    """

    experiment_name: str | None = None
    group: str | None = None
    tags: dict[str, str] | list[str] | None = None
    parent_run_id: str | None = None
    attempt: int | None = None
    git_commit: str | None = None
    python_version: str | None = None
    platform: str | None = None
    hostname: str | None = None
    started_cmd: str | None = None
    dataset_version: str | None = None
    seed: int | None = None
    extras: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return asdict(self)


@dataclass(slots=True)
class MetricEvent:
    """单条指标事件。

    Attributes:
        step: 指标对应的 step（epoch/global step）。
        timestamp: 事件时间（ISO8601）。
        metrics: 指标字典。
        split: 数据划分（train/valid/test）。
        phase: 阶段标识（fit/eval/infer）。
    """

    step: int
    timestamp: str
    metrics: dict[str, float]
    split: str = "train"
    phase: str = "fit"

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return asdict(self)


@dataclass(slots=True)
class RunContext:
    """单次实验运行上下文。

    该对象由 ``ExpRunner`` 在每个 run 开始时构造，并传入用户实验函数。

    Attributes:
        run_id: 当前运行唯一 ID（同时也是 run 目录名）。
        run_dir: 当前运行目录绝对路径。
        config: 当前运行最终配置字典。
        logger: 当前运行专属日志对象（输出到 run.log）。
        meta: 当前 run 元数据对象。

    Examples:
        >>> def exp_fn(ctx: RunContext):
        ...     lr = ctx.config["lr"]
        ...     ctx.logger.info("lr=%s", lr)
        ...     return {"score": 1.0 - lr}
    """

    run_id: str
    run_dir: Path
    config: dict[str, Any]
    logger: logging.Logger
    meta: RunMetadata = field(default_factory=RunMetadata)
    _metrics_jsonl_path: Path | None = field(default=None, repr=False)
    _trackers: list["Tracker"] = field(default_factory=list, repr=False)

    def log_metric(
        self,
        step: int,
        metrics: dict[str, float],
        split: str = "train",
        phase: str = "fit",
    ) -> None:
        """记录 step 级指标并通知 tracker。

        Args:
            step: 当前 step。
            metrics: 指标字典。
            split: 数据划分。
            phase: 运行阶段。

        Returns:
            None
        """
        event = MetricEvent(
            step=step,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metrics=metrics,
            split=split,
            phase=phase,
        )
        payload = event.to_dict()

        if self._metrics_jsonl_path is not None:
            utils.append_jsonl(self._metrics_jsonl_path, payload)

        for tracker in self._trackers:
            tracker.on_metric(self, event)


@dataclass(slots=True)
class RunSummary:
    """一次批量执行的汇总结果。

    Attributes:
        total: 本次执行计划中的配置总数。
        succeeded: 成功运行数量。
        failed: 失败运行数量。
        skipped: 跳过运行数量。
        duration_sec: 本次批量执行总耗时（秒）。
        failed_run_ids: 失败 run 的 ID 列表。

    Examples:
        >>> summary = RunSummary(4, 3, 1, 0, 2.35, ["20260301_xxx"])
        >>> summary.failed
        1
    """

    total: int
    succeeded: int
    failed: int
    skipped: int
    duration_sec: float
    failed_run_ids: list[str]
