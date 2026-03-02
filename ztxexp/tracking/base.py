"""追踪器协议定义。"""

from __future__ import annotations

from typing import Protocol

from ztxexp.types import MetricEvent, RunContext, RunMetadata


class Tracker(Protocol):
    """实验追踪器协议。

    所有追踪器都应实现生命周期三段回调：
    1. run 开始；
    2. 指标事件；
    3. run 结束。
    """

    def on_run_start(self, ctx: RunContext, meta: RunMetadata) -> None:
        """run 启动回调。"""

    def on_metric(self, ctx: RunContext, event: MetricEvent) -> None:
        """指标事件回调。"""

    def on_run_end(self, ctx: RunContext, summary: dict[str, object]) -> None:
        """run 结束回调。"""
