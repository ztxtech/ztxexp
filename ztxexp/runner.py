"""实验执行器。

本模块负责将配置列表调度为具体运行，并按 v2 协议写入产物：
- config.json
- run.json
- metrics.json（可选）
- artifacts/
- run.log / error.log（按需）
"""

from __future__ import annotations

import copy
import datetime as dt
import time
import traceback
import uuid
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, as_completed, wait
from pathlib import Path
from typing import Any, Callable

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
from ztxexp.types import RunContext, RunSummary

# 单次实验函数契约：输入 RunContext，输出 dict 或 None。
ExperimentFn = Callable[[RunContext], dict[str, Any] | None]


class SkipRun(Exception):
    """主动跳过当前运行。

    当用户实验函数希望“非失败地跳过”某个配置时，可以抛出该异常。
    运行结果将写为 ``status=skipped``。

    Examples:
        >>> raise SkipRun("配置不满足先验条件，跳过")
    """


def _utc_now_iso() -> str:
    """获取当前 UTC 时间（ISO8601 字符串）。

    Returns:
        str: 例如 ``2026-03-01T12:34:56.123456+00:00``。
    """
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _new_run_id() -> str:
    """生成 run_id。

    Returns:
        str: ``YYYYmmdd_HHMMSS_xxxxxxxx`` 格式的唯一 ID。
    """
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{uuid.uuid4().hex[:8]}"


def _run_payload(run_id: str, status: str) -> dict[str, Any]:
    """构造 run.json 初始结构。

    Args:
        run_id: 当前运行 ID。
        status: 当前状态值。

    Returns:
        dict[str, Any]: run.json 元数据字典。
    """
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
    }


def _write_error_log(run_dir: Path, stack_trace: str) -> None:
    """将堆栈写入 ``error.log``。

    Args:
        run_dir: 当前运行目录。
        stack_trace: 完整 traceback 文本。

    Returns:
        None
    """
    with open(run_dir / "error.log", "w", encoding="utf-8") as handle:
        handle.write(stack_trace)


def _failure_record_from_exception(exc: Exception) -> dict[str, Any]:
    """构造“运行前失败”记录。

    当并行框架层面异常导致无法产生正常 run_id 时，使用该函数构造
    一个占位失败记录，保证汇总过程不中断。

    Args:
        exc: 捕获到的异常对象。

    Returns:
        dict[str, Any]: 最小失败记录。
    """
    return {
        "run_id": f"unstarted_{uuid.uuid4().hex[:8]}",
        "status": RUN_STATUS_FAILED,
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }


def _execute_single_run(
    config: dict[str, Any],
    exp_function: ExperimentFn,
    results_root: str | Path,
) -> dict[str, Any]:
    """执行单个实验并写入标准产物。

    Args:
        config: 单次运行配置字典。
        exp_function: 用户实验函数。
        results_root: 结果根目录。

    Returns:
        dict[str, Any]: 运行结果摘要，格式为：
            ``{"run_id": str, "status": str, "error_type": str|None, "error_message": str|None}``。

    Raises:
        无。函数内部会捕获所有异常并写入失败状态。

    Examples:
        >>> def exp_fn(ctx):
        ...     return {"score": 0.9}
        >>> rec = _execute_single_run({"lr": 1e-3}, exp_fn, "./results_demo")
        >>> rec["status"] in {"succeeded", "failed", "skipped"}
        True
    """
    start = time.time()
    run_id = _new_run_id()
    run_dir = Path(results_root) / run_id
    artifacts_dir = run_dir / "artifacts"

    # 先建目录，保证后续文件写入稳定。
    utils.create_dir(run_dir)
    utils.create_dir(artifacts_dir)

    logger = utils.setup_logger(f"ztxexp.run.{run_id}", str(run_dir / "run.log"))

    run_meta = _run_payload(run_id, RUN_STATUS_RUNNING)
    config_payload = copy.deepcopy(config)
    utils.save_json(config_payload, run_dir / "config.json")
    utils.save_json(run_meta, run_dir / "run.json")

    ctx = RunContext(
        run_id=run_id,
        run_dir=run_dir,
        config=config_payload,
        logger=logger,
    )

    status = RUN_STATUS_SUCCEEDED
    error_type: str | None = None
    error_message: str | None = None

    try:
        result = exp_function(ctx)
        if result is not None and not isinstance(result, dict):
            raise TypeError("Experiment function must return dict or None.")

        if isinstance(result, dict):
            utils.save_json(result, run_dir / "metrics.json")

    except SkipRun as exc:
        status = RUN_STATUS_SKIPPED
        error_type = type(exc).__name__
        error_message = str(exc)
        logger.warning("Run %s skipped: %s", run_id, exc)

    except Exception as exc:  # pragma: no cover - 集成测试覆盖
        status = RUN_STATUS_FAILED
        error_type = type(exc).__name__
        error_message = str(exc)
        stack_trace = traceback.format_exc()
        _write_error_log(run_dir, stack_trace)
        logger.exception("Run %s failed", run_id)

    finally:
        run_meta["status"] = status
        run_meta["finished_at"] = _utc_now_iso()
        run_meta["duration_sec"] = round(time.time() - start, 6)
        run_meta["error_type"] = error_type
        run_meta["error_message"] = error_message
        utils.save_json(run_meta, run_dir / "run.json")

        # Windows 下不关闭 handler 会导致目录删除失败。
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    return {
        "run_id": run_id,
        "status": status,
        "error_type": error_type,
        "error_message": error_message,
    }


class ExpRunner:
    """实验执行器。

    Args:
        configs: 待运行配置列表。
        results_root: 结果根目录。
        exp_function: 默认实验函数（可在 ``run`` 时覆盖）。

    Notes:
        支持四种执行模式：
        - ``sequential``
        - ``process_pool``
        - ``joblib``
        - ``dynamic``（实验特性）
    """

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
    ) -> RunSummary:
        """执行全部配置并返回汇总。

        Args:
            exp_function: 实验函数，若为 ``None`` 则使用构造器传入的默认函数。
            mode: 执行模式。
            workers: 并行 worker 数量。
            cpu_threshold: dynamic 模式的 CPU 提交阈值。
            execution_mode: 兼容旧参数名（等同 mode）。
            num_workers: 兼容旧参数名（等同 workers）。
            dynamic_cpu_threshold: 兼容旧参数名（等同 cpu_threshold）。

        Returns:
            RunSummary: 本次批量执行汇总。

        Raises:
            ValueError: 未提供实验函数，或执行模式非法。

        Examples:
            >>> runner = ExpRunner([{"lr": 1e-3}], "./results_demo")
            >>> def exp_fn(ctx):
            ...     return {"score": 1.0}
            >>> summary = runner.run(exp_fn, mode="sequential")
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
        start = time.time()

        if total == 0:
            return RunSummary(
                total=0,
                succeeded=0,
                failed=0,
                skipped=0,
                duration_sec=0.0,
                failed_run_ids=[],
            )

        if mode == "sequential":
            records = [
                _execute_single_run(config, experiment, self.results_root)
                for config in self.configs
            ]
        elif mode == "process_pool":
            records = self._run_process_pool(experiment, workers)
        elif mode == "joblib":
            records = self._run_joblib(experiment, workers)
        elif mode == "dynamic":
            records = self._run_dynamic(experiment, workers, cpu_threshold)
        else:
            raise ValueError(
                f"Invalid mode '{mode}'. Choose from sequential/process_pool/joblib/dynamic."
            )

        duration = round(time.time() - start, 6)
        return self._summarize(records, total, duration)

    def _run_process_pool(self, exp_function: ExperimentFn, workers: int) -> list[dict[str, Any]]:
        """使用 ProcessPoolExecutor 并行执行。

        Args:
            exp_function: 实验函数。
            workers: 最大并发进程数。

        Returns:
            list[dict[str, Any]]: 每个配置对应的执行记录列表。
        """
        records: list[dict[str, Any]] = []
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_map = {
                executor.submit(
                    _execute_single_run,
                    config,
                    exp_function,
                    self.results_root,
                ): config
                for config in self.configs
            }
            for future in as_completed(future_map):
                try:
                    records.append(future.result())
                except Exception as exc:  # pragma: no cover
                    records.append(_failure_record_from_exception(exc))
        return records

    def _run_joblib(self, exp_function: ExperimentFn, workers: int) -> list[dict[str, Any]]:
        """使用 joblib 并行执行。

        Args:
            exp_function: 实验函数。
            workers: 并发进程数。

        Returns:
            list[dict[str, Any]]: 执行记录列表。
        """
        try:
            return Parallel(n_jobs=workers, prefer="processes")(
                delayed(_execute_single_run)(config, exp_function, self.results_root)
                for config in self.configs
            )
        except Exception as exc:  # pragma: no cover
            return [_failure_record_from_exception(exc) for _ in self.configs]

    def _run_dynamic(
        self,
        exp_function: ExperimentFn,
        workers: int,
        cpu_threshold: int,
    ) -> list[dict[str, Any]]:
        """动态调度执行（实验特性）。

        调度规则：
        1. in-flight 任务数不超过 ``workers``；
        2. 当前 CPU 使用率低于阈值才提交新任务。

        Args:
            exp_function: 实验函数。
            workers: 最大并发进程数。
            cpu_threshold: CPU 提交阈值（百分比）。

        Returns:
            list[dict[str, Any]]: 执行记录列表。
        """
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
        """将执行记录聚合为 ``RunSummary``。

        Args:
            records: 单条执行记录列表。
            total: 配置总数。
            duration_sec: 总耗时（秒）。

        Returns:
            RunSummary: 聚合结果。
        """
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
