"""ztxexp 对外公开的运行时数据结构。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class RunContext:
    """单次实验运行上下文。

    该对象由 ``ExpRunner`` 在每个 run 开始时构造，并传入用户实验函数。

    Attributes:
        run_id: 当前运行唯一 ID（同时也是 run 目录名）。
        run_dir: 当前运行目录绝对路径。
        config: 当前运行最终配置字典。
        logger: 当前运行专属日志对象（输出到 run.log）。

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
