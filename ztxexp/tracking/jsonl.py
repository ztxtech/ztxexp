"""JSONL 追踪器实现。"""

from __future__ import annotations

from typing import Any

from ztxexp import utils
from ztxexp.types import MetricEvent, RunContext, RunMetadata


class JsonlTracker:
    """将生命周期事件写入 ``events.jsonl`` 的轻量追踪器。

    Args:
        events_filename: 事件文件名。
    """

    def __init__(self, events_filename: str = "events.jsonl"):
        self.events_filename = events_filename

    def _events_path(self, ctx: RunContext):
        return ctx.run_dir / self.events_filename

    def _append(self, ctx: RunContext, payload: dict[str, Any]) -> None:
        utils.append_jsonl(self._events_path(ctx), payload)

    def on_run_start(self, ctx: RunContext, meta: RunMetadata) -> None:
        """记录 run 启动事件。"""
        self._append(
            ctx,
            {
                "event": "run_start",
                "run_id": ctx.run_id,
                "timestamp": utils.utc_now_iso(),
                "meta": meta.to_dict(),
            },
        )

    def on_metric(self, ctx: RunContext, event: MetricEvent) -> None:
        """记录指标事件。"""
        self._append(
            ctx,
            {
                "event": "metric",
                "run_id": ctx.run_id,
                "payload": event.to_dict(),
            },
        )

    def on_run_end(self, ctx: RunContext, summary: dict[str, object]) -> None:
        """记录 run 结束事件。"""
        self._append(
            ctx,
            {
                "event": "run_end",
                "run_id": ctx.run_id,
                "timestamp": utils.utc_now_iso(),
                "summary": summary,
            },
        )
