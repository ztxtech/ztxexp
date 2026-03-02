"""实验执行器。

本模块负责将配置列表调度为具体运行，并按 v2 协议写入产物：
- config.json
- run.json
- meta.json（可选）
- metrics.json（可选）
- metrics.jsonl（可选）
- events.jsonl（可选）
- artifacts/
- run.log / error.log（按需）
"""

from __future__ import annotations

import copy
import platform as py_platform
import socket
import subprocess
import sys
import time
import traceback
import uuid
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, as_completed, wait
from pathlib import Path
from typing import Any, Callable, Sequence

import psutil
from joblib import Parallel, delayed

from ztxexp import utils
from ztxexp.constants import (
    RUN_SCHEMA_VERSION,
    RUN_STATUS_FAILED,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SKIPPED,
    RUN_STATUS_SUCCEEDED,
)
from ztxexp.tracking import JsonlTracker, MlflowTracker, Tracker, WandbTracker
from ztxexp.types import RunContext, RunMetadata, RunSummary

# 单次实验函数契约：输入 RunContext，输出 dict 或 None。
ExperimentFn = Callable[[RunContext], dict[str, Any] | None]


class SkipRun(Exception):
    """主动跳过当前运行。

    在 ``exp_fn`` 中抛出该异常时，当前 run 会被标记为 ``skipped``，
    而不是 ``failed``。适用于“业务上不合法、无需重试”的配置分支。

    Examples:
        >>> from ztxexp import SkipRun
        >>> def exp_fn(ctx):
        ...     if ctx.config.get("batch_size", 0) <= 0:
        ...         raise SkipRun("batch_size must be positive")
        ...     return {"score": 0.9}
    """


def _utc_now_iso() -> str:
    """获取当前 UTC 时间（ISO8601 字符串）。"""
    return utils.utc_now_iso()


def _new_run_id() -> str:
    """生成 run_id。"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{uuid.uuid4().hex[:8]}"


def _run_payload(run_id: str, status: str) -> dict[str, Any]:
    """构造 run.json 初始结构。"""
    now = _utc_now_iso()
    return {
        "schema_version": RUN_SCHEMA_VERSION,
        "run_id": run_id,
        "status": status,
        "started_at": now,
        "finished_at": None,
        "duration_sec": None,
        "error_type": None,
        "error_message": None,
        "experiment_name": None,
        "group": None,
        "tags": None,
        "parent_run_id": None,
        "attempt": 1,
        "retry_count": 0,
    }


def _write_error_log(run_dir: Path, stack_trace: str) -> None:
    """将堆栈写入 ``error.log``。"""
    with open(run_dir / "error.log", "w", encoding="utf-8") as handle:
        handle.write(stack_trace)


def _failure_record_from_exception(exc: Exception) -> dict[str, Any]:
    """构造“运行前失败”记录。"""
    return {
        "run_id": f"unstarted_{uuid.uuid4().hex[:8]}",
        "status": RUN_STATUS_FAILED,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "retry_count": 0,
    }


def _get_git_commit() -> str | None:
    """读取当前仓库 commit。"""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return None
        commit = proc.stdout.strip()
        return commit or None
    except Exception:  # pragma: no cover
        return None


def _normalize_seed(value: Any) -> int | None:
    """归一化 seed 值。"""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _collect_run_metadata(
    config: dict[str, Any],
    metadata: RunMetadata | None,
    attempt: int,
) -> RunMetadata:
    """采集并补全运行元数据。"""
    merged = copy.deepcopy(metadata) if metadata is not None else RunMetadata()
    if not isinstance(merged, RunMetadata):
        merged = RunMetadata(**utils.as_plain_dict(merged))

    merged.attempt = attempt
    merged.git_commit = merged.git_commit or _get_git_commit()
    merged.python_version = merged.python_version or py_platform.python_version()
    merged.platform = merged.platform or py_platform.platform()
    merged.hostname = merged.hostname or socket.gethostname()
    merged.started_cmd = merged.started_cmd or " ".join(sys.argv)
    merged.dataset_version = (
        merged.dataset_version
        or str(config.get("dataset_version") or config.get("data_version") or "")
        or None
    )
    merged.seed = merged.seed if merged.seed is not None else _normalize_seed(config.get("seed"))
    if merged.extras is None:
        merged.extras = {}
    return merged


def _is_retryable(exc: Exception, retry_on: Sequence[str]) -> bool:
    """判断异常是否可重试。"""
    if "Exception" in retry_on:
        return True
    class_names = {klass.__name__ for klass in type(exc).mro()}
    return any(name in class_names for name in retry_on)


def _build_trackers(
    tracker_specs: list[dict[str, Any]] | None,
    trackers: list[Tracker] | None,
) -> list[Tracker]:
    """构造追踪器实例列表。"""
    built = list(trackers or [])

    for spec in tracker_specs or []:
        tracker_type = str(spec.get("type", "")).lower()
        kwargs = dict(spec.get("kwargs", {}))

        if tracker_type == "jsonl":
            built.append(JsonlTracker(**kwargs))
        elif tracker_type == "mlflow":
            built.append(MlflowTracker(**kwargs))
        elif tracker_type == "wandb":
            built.append(WandbTracker(**kwargs))

    return built


def _safe_tracker_start(trackers: list[Tracker], ctx: RunContext, meta: RunMetadata) -> None:
    """安全执行 on_run_start 回调。"""
    for tracker in trackers:
        try:
            tracker.on_run_start(ctx, meta)
        except Exception as exc:  # pragma: no cover
            ctx.logger.warning("Tracker %s on_run_start failed: %s", type(tracker).__name__, exc)


def _safe_tracker_end(trackers: list[Tracker], ctx: RunContext, summary: dict[str, object]) -> None:
    """安全执行 on_run_end 回调。"""
    for tracker in trackers:
        try:
            tracker.on_run_end(ctx, summary)
        except Exception as exc:  # pragma: no cover
            ctx.logger.warning("Tracker %s on_run_end failed: %s", type(tracker).__name__, exc)


def _append_event(run_dir: Path, event: dict[str, Any]) -> None:
    """向 events.jsonl 追加事件。"""
    utils.append_jsonl(run_dir / "events.jsonl", event)


def _execute_single_run(
    config: dict[str, Any],
    exp_function: ExperimentFn,
    results_root: str | Path,
    metadata: RunMetadata | None = None,
    max_attempts: int = 1,
    retry_on: tuple[str, ...] = ("Exception",),
    tracker_specs: list[dict[str, Any]] | None = None,
    trackers: list[Tracker] | None = None,
) -> dict[str, Any]:
    """执行单个实验并写入标准产物。"""
    started = time.time()
    run_id = _new_run_id()
    run_dir = Path(results_root) / run_id
    artifacts_dir = run_dir / "artifacts"
    checkpoints_dir = run_dir / "checkpoints"

    utils.create_dir(run_dir)
    utils.create_dir(artifacts_dir)
    utils.create_dir(checkpoints_dir)

    logger = utils.setup_logger(f"ztxexp.run.{run_id}", str(run_dir / "run.log"))

    run_meta = _run_payload(run_id, RUN_STATUS_RUNNING)
    config_payload = copy.deepcopy(config)
    utils.save_json(config_payload, run_dir / "config.json")
    utils.save_json(run_meta, run_dir / "run.json")

    run_metadata = _collect_run_metadata(config_payload, metadata, attempt=1)
    utils.save_json(run_metadata.to_dict(), run_dir / "meta.json")

    resolved_trackers = _build_trackers(tracker_specs, trackers)
    ctx = RunContext(
        run_id=run_id,
        run_dir=run_dir,
        config=config_payload,
        logger=logger,
        meta=run_metadata,
        _metrics_jsonl_path=run_dir / "metrics.jsonl",
        _trackers=resolved_trackers,
    )

    _safe_tracker_start(resolved_trackers, ctx, run_metadata)
    _append_event(
        run_dir,
        {
            "event": "start",
            "run_id": run_id,
            "timestamp": _utc_now_iso(),
        },
    )

    status = RUN_STATUS_SUCCEEDED
    error_type: str | None = None
    error_message: str | None = None
    attempts_executed = 0
    retry_budget = max(1, int(max_attempts))

    try:
        for attempt in range(1, retry_budget + 1):
            attempts_executed = attempt
            ctx.meta = _collect_run_metadata(config_payload, ctx.meta, attempt=attempt)
            utils.save_json(ctx.meta.to_dict(), run_dir / "meta.json")

            run_meta["attempt"] = attempt
            run_meta["retry_count"] = attempt - 1
            run_meta["status"] = RUN_STATUS_RUNNING
            utils.save_json(run_meta, run_dir / "run.json")

            try:
                result = exp_function(ctx)
                if result is not None and not isinstance(result, dict):
                    raise TypeError("Experiment function must return dict or None.")

                if isinstance(result, dict):
                    utils.save_json(result, run_dir / "metrics.json")

                status = RUN_STATUS_SUCCEEDED
                error_type = None
                error_message = None
                break

            except SkipRun as exc:
                status = RUN_STATUS_SKIPPED
                error_type = type(exc).__name__
                error_message = str(exc)
                logger.warning("Run %s skipped: %s", run_id, exc)
                _append_event(
                    run_dir,
                    {
                        "event": "skip",
                        "run_id": run_id,
                        "attempt": attempt,
                        "timestamp": _utc_now_iso(),
                        "reason": str(exc),
                    },
                )
                break

            except Exception as exc:
                status = RUN_STATUS_FAILED
                error_type = type(exc).__name__
                error_message = str(exc)
                stack_trace = traceback.format_exc()

                can_retry = attempt < retry_budget and _is_retryable(exc, retry_on)
                if can_retry:
                    _append_event(
                        run_dir,
                        {
                            "event": "retry",
                            "run_id": run_id,
                            "attempt": attempt,
                            "timestamp": _utc_now_iso(),
                            "error_type": error_type,
                            "error_message": error_message,
                        },
                    )
                    logger.warning(
                        "Run %s attempt %s failed (%s), retrying...",
                        run_id,
                        attempt,
                        error_type,
                    )
                    continue

                _write_error_log(run_dir, stack_trace)
                _append_event(
                    run_dir,
                    {
                        "event": "error",
                        "run_id": run_id,
                        "attempt": attempt,
                        "timestamp": _utc_now_iso(),
                        "error_type": error_type,
                        "error_message": error_message,
                    },
                )
                logger.exception("Run %s failed", run_id)
                break

    finally:
        run_meta["status"] = status
        run_meta["finished_at"] = _utc_now_iso()
        run_meta["duration_sec"] = round(time.time() - started, 6)
        run_meta["error_type"] = error_type
        run_meta["error_message"] = error_message
        run_meta["experiment_name"] = ctx.meta.experiment_name
        run_meta["group"] = ctx.meta.group
        run_meta["tags"] = ctx.meta.tags
        run_meta["parent_run_id"] = ctx.meta.parent_run_id
        run_meta["attempt"] = attempts_executed or 1
        run_meta["retry_count"] = max((attempts_executed or 1) - 1, 0)
        utils.save_json(run_meta, run_dir / "run.json")

        summary_payload: dict[str, object] = {
            "run_id": run_id,
            "status": status,
            "error_type": error_type,
            "error_message": error_message,
            "retry_count": run_meta["retry_count"],
            "attempt": run_meta["attempt"],
        }
        _append_event(
            run_dir,
            {
                "event": "end",
                "run_id": run_id,
                "timestamp": _utc_now_iso(),
                "summary": summary_payload,
            },
        )
        _safe_tracker_end(resolved_trackers, ctx, summary_payload)

        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    return {
        "run_id": run_id,
        "status": status,
        "error_type": error_type,
        "error_message": error_message,
        "retry_count": run_meta["retry_count"],
    }


class ExpRunner:
    """实验执行器。"""

    def __init__(
        self,
        configs: list[dict[str, Any]],
        results_root: str | Path,
        exp_function: ExperimentFn | None = None,
    ):
        self.configs = [dict(config) for config in configs]
        self.results_root = Path(results_root)
        self.exp_function = exp_function
        utils.create_dir(self.results_root)

    def run(
        self,
        exp_function: ExperimentFn | None = None,
        mode: str = "sequential",
        workers: int = 1,
        cpu_threshold: int = 80,
        execution_mode: str | None = None,
        num_workers: int | None = None,
        dynamic_cpu_threshold: int | None = None,
        metadata: RunMetadata | None = None,
        max_attempts: int = 1,
        retry_on: tuple[str, ...] = ("Exception",),
        tracker_specs: list[dict[str, Any]] | None = None,
        trackers: list[Tracker] | None = None,
    ) -> RunSummary:
        """执行全部配置并返回汇总。

        Args:
            exp_function: 单次实验函数，签名应为
                ``exp_fn(ctx: RunContext) -> dict | None``。
            mode: 执行模式。可选
                ``sequential`` / ``process_pool`` / ``joblib`` / ``dynamic``。
            workers: 并行 worker 数。
            cpu_threshold: ``dynamic`` 模式提交新任务时的 CPU 阈值。
            execution_mode: 兼容参数，等价于 ``mode``。
            num_workers: 兼容参数，等价于 ``workers``。
            dynamic_cpu_threshold: 兼容参数，等价于 ``cpu_threshold``。
            metadata: 运行元数据模板。框架会补全可采集字段。
            max_attempts: 每个配置最大尝试次数（失败重试上限）。
            retry_on: 可重试异常名集合（支持父类名，如 ``Exception``）。
            tracker_specs: 追踪器规格列表（字符串模式构造 tracker）。
            trackers: 追踪器实例列表（当前进程内对象）。

        Returns:
            RunSummary: 本次批量执行汇总（成功/失败/跳过计数与耗时）。

        Raises:
            ValueError: 未提供 ``exp_function`` 或 ``mode`` 不合法时抛出。

        Notes:
            - ``exp_fn`` 返回 ``dict`` 时自动写入 ``metrics.json``；
            - ``exp_fn`` 返回 ``None`` 时不写 ``metrics.json``；
            - 返回非 ``dict|None`` 会判定为失败并写 ``error.log``；
            - 抛出 ``SkipRun`` 会标记为 ``skipped``；
            - 成功判定以 ``run.json.status == succeeded`` 为准。

        Examples:
            >>> def exp_fn(ctx: RunContext):
            ...     return {"score": 0.9}
            >>> summary = ExpRunner([{"lr": 0.001}], "./results").run(exp_fn)
            >>> summary.total
            1
        """
        if execution_mode is not None:
            mode = execution_mode
        if num_workers is not None:
            workers = num_workers
        if dynamic_cpu_threshold is not None:
            cpu_threshold = dynamic_cpu_threshold

        experiment = exp_function or self.exp_function
        if experiment is None:
            raise ValueError("exp_function is required.")

        total = len(self.configs)
        started = time.time()

        if total == 0:
            return RunSummary(
                total=0,
                succeeded=0,
                failed=0,
                skipped=0,
                duration_sec=0.0,
                failed_run_ids=[],
            )

        resolved_specs = list(tracker_specs or [])
        has_jsonl_spec = any(
            str(spec.get("type", "")).lower() == "jsonl" for spec in resolved_specs
        )
        has_jsonl_instance = any(isinstance(tracker, JsonlTracker) for tracker in (trackers or []))
        if not has_jsonl_spec and not has_jsonl_instance:
            resolved_specs.append({"type": "jsonl", "kwargs": {}})

        if mode == "sequential":
            records = [
                _execute_single_run(
                    config=config,
                    exp_function=experiment,
                    results_root=self.results_root,
                    metadata=metadata,
                    max_attempts=max_attempts,
                    retry_on=retry_on,
                    tracker_specs=resolved_specs,
                    trackers=trackers,
                )
                for config in self.configs
            ]
        elif mode == "process_pool":
            if trackers:
                print("Live tracker instances are ignored in process_pool mode.")
            records = self._run_process_pool(
                exp_function=experiment,
                workers=workers,
                metadata=metadata,
                max_attempts=max_attempts,
                retry_on=retry_on,
                tracker_specs=resolved_specs,
            )
        elif mode == "joblib":
            if trackers:
                print("Live tracker instances are ignored in joblib mode.")
            records = self._run_joblib(
                exp_function=experiment,
                workers=workers,
                metadata=metadata,
                max_attempts=max_attempts,
                retry_on=retry_on,
                tracker_specs=resolved_specs,
            )
        elif mode == "dynamic":
            if trackers:
                print("Live tracker instances are ignored in dynamic mode.")
            records = self._run_dynamic(
                exp_function=experiment,
                workers=workers,
                cpu_threshold=cpu_threshold,
                metadata=metadata,
                max_attempts=max_attempts,
                retry_on=retry_on,
                tracker_specs=resolved_specs,
            )
        else:
            raise ValueError(
                f"Invalid mode '{mode}'. Choose from sequential/process_pool/joblib/dynamic."
            )

        duration = round(time.time() - started, 6)
        return self._summarize(records, total, duration)

    def _run_process_pool(
        self,
        exp_function: ExperimentFn,
        workers: int,
        metadata: RunMetadata | None,
        max_attempts: int,
        retry_on: tuple[str, ...],
        tracker_specs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """使用 ProcessPoolExecutor 并行执行。"""
        records: list[dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(
                    _execute_single_run,
                    config,
                    exp_function,
                    self.results_root,
                    metadata,
                    max_attempts,
                    retry_on,
                    tracker_specs,
                    None,
                ): config
                for config in self.configs
            }
            for future in as_completed(future_map):
                try:
                    records.append(future.result())
                except Exception as exc:  # pragma: no cover
                    records.append(_failure_record_from_exception(exc))
        return records

    def _run_joblib(
        self,
        exp_function: ExperimentFn,
        workers: int,
        metadata: RunMetadata | None,
        max_attempts: int,
        retry_on: tuple[str, ...],
        tracker_specs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """使用 joblib 并行执行。"""
        try:
            return Parallel(n_jobs=workers, prefer="processes")(
                delayed(_execute_single_run)(
                    config,
                    exp_function,
                    self.results_root,
                    metadata,
                    max_attempts,
                    retry_on,
                    tracker_specs,
                    None,
                )
                for config in self.configs
            )
        except Exception as exc:  # pragma: no cover
            return [_failure_record_from_exception(exc) for _ in self.configs]

    def _run_dynamic(
        self,
        exp_function: ExperimentFn,
        workers: int,
        cpu_threshold: int,
        metadata: RunMetadata | None,
        max_attempts: int,
        retry_on: tuple[str, ...],
        tracker_specs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """动态调度执行（实验特性）。"""
        pending = deque(self.configs)
        in_flight: dict[Any, dict[str, Any]] = {}
        records: list[dict[str, Any]] = []

        with ProcessPoolExecutor(max_workers=workers) as executor:
            while pending or in_flight:
                cpu_usage = psutil.cpu_percent(interval=0.2)

                while pending and len(in_flight) < workers and cpu_usage < cpu_threshold:
                    config = pending.popleft()
                    future = executor.submit(
                        _execute_single_run,
                        config,
                        exp_function,
                        self.results_root,
                        metadata,
                        max_attempts,
                        retry_on,
                        tracker_specs,
                        None,
                    )
                    in_flight[future] = config
                    cpu_usage = psutil.cpu_percent(interval=0.0)

                if not in_flight:
                    time.sleep(0.2)
                    continue

                done, _ = wait(
                    in_flight.keys(),
                    timeout=0.5,
                    return_when=FIRST_COMPLETED,
                )

                for future in done:
                    in_flight.pop(future, None)
                    try:
                        records.append(future.result())
                    except Exception as exc:  # pragma: no cover
                        records.append(_failure_record_from_exception(exc))

        return records

    def _summarize(
        self,
        records: list[dict[str, Any]],
        total: int,
        duration_sec: float,
    ) -> RunSummary:
        """将执行记录聚合为 ``RunSummary``。"""
        succeeded = sum(1 for record in records if record.get("status") == RUN_STATUS_SUCCEEDED)
        failed = sum(1 for record in records if record.get("status") == RUN_STATUS_FAILED)
        skipped = sum(1 for record in records if record.get("status") == RUN_STATUS_SKIPPED)
        failed_run_ids = [
            str(record.get("run_id"))
            for record in records
            if record.get("status") == RUN_STATUS_FAILED
        ]

        return RunSummary(
            total=total,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            duration_sec=duration_sec,
            failed_run_ids=failed_run_ids,
        )
