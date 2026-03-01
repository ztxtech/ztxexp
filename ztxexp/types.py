"""Public dataclasses used by the experiment runtime."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class RunContext:
    """Runtime context passed to each experiment function."""

    run_id: str
    run_dir: Path
    config: dict[str, Any]
    logger: logging.Logger


@dataclass(slots=True)
class RunSummary:
    """Aggregated execution summary for a runner invocation."""

    total: int
    succeeded: int
    failed: int
    skipped: int
    duration_sec: float
    failed_run_ids: list[str]
