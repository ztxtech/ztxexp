"""通用工具函数集合。

该模块被 manager/runner/analyzer 等核心组件复用，设计原则：
1. 纯工具、低耦合；
2. 尽量无全局副作用；
3. 对可选依赖提供明确错误提示。
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
import pathlib
import random
import re
import shutil
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

import psutil


def _json_default(value: Any) -> Any:
    """JSON 序列化兜底转换器。

    Args:
        value: 需要序列化的对象。

    Returns:
        Any: 可被 ``json.dump`` 序列化的替代对象。

    Raises:
        TypeError: 无法转换为 JSON 兼容格式时抛出。
    """
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, tuple):
        return list(value)
    if hasattr(value, "__dict__"):
        return value.__dict__
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _require_dependency(module_name: str, extra_name: str) -> Any:
    """按需导入可选依赖。

    Args:
        module_name: 模块名，例如 ``torch``。
        extra_name: 对应 pip extras 名称，例如 ``torch``。

    Returns:
        module: 导入后的模块对象。

    Raises:
        ImportError: 依赖缺失时抛出并附带安装提示。
    """
    try:
        return __import__(module_name)
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            f"Optional dependency '{module_name}' is required for this function. "
            f"Install with: pip install ztxexp[{extra_name}]"
        ) from exc


def add_to_sys_path(path: str | Path) -> None:
    """将目录加入 ``sys.path``（若尚未存在）。

    Args:
        path: 目标目录。

    Returns:
        None

    Examples:
        >>> add_to_sys_path("./")
    """
    abs_path = str(Path(path).resolve())
    if abs_path not in sys.path:
        sys.path.insert(0, abs_path)
        print(f"Added '{abs_path}' to system path.")


def setup_logger(name: str, log_file: str | Path, level: int = logging.INFO) -> logging.Logger:
    """创建或复用日志器（文件 + 控制台）。

    Args:
        name: logger 名称。
        log_file: 文件日志路径。
        level: 日志级别。

    Returns:
        logging.Logger: 配置完成的 logger。

    Notes:
        同名 logger 若已存在 handler，则直接复用，避免重复输出。
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    if logger.handlers:
        return logger

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def save_json(data: dict[str, Any], file_path: str | Path, indent: int = 2) -> None:
    """保存字典为 JSON 文件。

    Args:
        data: 目标字典。
        file_path: 输出路径。
        indent: 缩进空格数。

    Returns:
        None
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=indent, default=_json_default)


def load_json(file_path: str | Path) -> dict[str, Any] | None:
    """读取 JSON 字典文件。

    Args:
        file_path: 文件路径。

    Returns:
        dict[str, Any] | None:
            - 文件存在且顶层为 dict 时返回字典；
            - 文件不存在或顶层非 dict 时返回 None。
    """
    path = Path(file_path)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return data
    return None


def save_dill(obj: object, file_path: str | Path) -> None:
    """使用 dill 序列化对象到文件。

    Args:
        obj: 任意 Python 对象。
        file_path: 输出路径。

    Returns:
        None
    """
    dill = _require_dependency("dill", "core")
    with open(file_path, "wb") as handle:
        dill.dump(obj, handle)


def load_dill(file_path: str | Path) -> object:
    """从 dill 文件反序列化对象。

    Args:
        file_path: 输入路径。

    Returns:
        object: 反序列化后的对象。
    """
    dill = _require_dependency("dill", "core")
    with open(file_path, "rb") as handle:
        return dill.load(handle)


def save_torch_model(model: Any, optimizer: Any | None, epoch: int, path: str | Path) -> None:
    """保存 PyTorch checkpoint。

    Args:
        model: ``torch.nn.Module`` 实例。
        optimizer: ``torch.optim.Optimizer`` 或 None。
        epoch: 当前训练轮数。
        path: 输出路径。

    Returns:
        None
    """
    torch = _require_dependency("torch", "torch")
    torch.save(
        {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict() if optimizer else None,
        },
        path,
    )


def load_torch_model(
    model: Any,
    optimizer: Any | None,
    path: str | Path,
) -> tuple[Any, Any | None, int]:
    """加载 PyTorch checkpoint。

    Args:
        model: ``torch.nn.Module`` 实例。
        optimizer: ``torch.optim.Optimizer`` 或 None。
        path: checkpoint 路径。

    Returns:
        tuple: ``(model, optimizer, epoch)``。
    """
    torch = _require_dependency("torch", "torch")
    checkpoint = torch.load(path, map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer and checkpoint.get("optimizer_state_dict"):
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    epoch = checkpoint.get("epoch", 0)
    return model, optimizer, epoch


@contextmanager
def timer(name: str, logger: logging.Logger | None = None) -> Iterator[None]:
    """计时代码块。

    Args:
        name: 计时标签。
        logger: 可选日志器。为空则打印到标准输出。

    Yields:
        None

    Examples:
        >>> with timer("step"):
        ...     _ = sum(range(100))
    """
    t0 = time.time()
    yield
    elapsed = time.time() - t0
    message = f"[{name}] done in {elapsed:.4f}s"
    if logger:
        logger.info(message)
    else:
        print(message)


def format_time_delta(seconds: float) -> str:
    """将秒数格式化为 ``Hh Mm Ss``。

    Args:
        seconds: 总秒数。

    Returns:
        str: 例如 ``'1h 2m 3s'``。
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}h {m}m {s}s"


def utc_now_iso() -> str:
    """返回当前 UTC 时间的 ISO8601 字符串。"""
    return datetime.now(timezone.utc).isoformat()


def get_memory_usage() -> str:
    """获取当前进程内存占用。

    Returns:
        str: 形如 ``'123.45 MB'``。
    """
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return f"{mem_info.rss / 1024 ** 2:.2f} MB"


def config_to_hash(config: dict[str, Any], length: int = 8) -> str:
    """将配置字典映射为稳定短哈希。

    Args:
        config: 配置字典。
        length: 截断长度。

    Returns:
        str: SHA256 前缀。

    Examples:
        >>> config_to_hash({"lr": 0.01}, length=6)
        '...'
    """
    sorted_config_str = json.dumps(config, sort_keys=True, default=_json_default)
    hash_object = hashlib.sha256(sorted_config_str.encode("utf-8"))
    return hash_object.hexdigest()[:length]


def as_plain_dict(value: Any) -> dict[str, Any]:
    """将常见配置对象统一转换为普通字典。

    支持输入类型：
    1. ``Mapping``：返回深拷贝字典；
    2. dataclass 实例：使用 ``dataclasses.asdict``；
    3. 具有 ``__dict__`` 的对象（如 ``argparse.Namespace``）。

    Args:
        value: 待转换对象。

    Returns:
        dict[str, Any]: 转换后的普通字典。

    Raises:
        TypeError: 输入对象不支持转换时抛出。

    Examples:
        >>> as_plain_dict({"lr": 0.001})
        {'lr': 0.001}
    """
    if isinstance(value, Mapping):
        return copy.deepcopy(dict(value))
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return copy.deepcopy(vars(value))
    raise TypeError(f"Cannot convert type '{type(value).__name__}' to dict.")


def flatten_dict(
    data: Mapping[str, Any],
    parent_key: str = "",
    sep: str = ".",
) -> dict[str, Any]:
    """将嵌套字典扁平化为单层字典。

    Args:
        data: 输入嵌套字典。
        parent_key: 父级前缀键，通常由递归内部使用。
        sep: 键路径分隔符。

    Returns:
        dict[str, Any]: 扁平化结果。示例：``{"a": {"b": 1}} -> {"a.b": 1}``。

    Examples:
        >>> flatten_dict({"model": {"name": "tiny", "layers": 12}})
        {'model.name': 'tiny', 'model.layers': 12}
    """
    flat: dict[str, Any] = {}
    for key, value in data.items():
        new_key = f"{parent_key}{sep}{key}" if parent_key else str(key)
        if isinstance(value, Mapping):
            flat.update(flatten_dict(value, parent_key=new_key, sep=sep))
        else:
            flat[new_key] = value
    return flat


def unflatten_dict(data: Mapping[str, Any], sep: str = ".") -> dict[str, Any]:
    """将扁平字典还原为嵌套字典。

    Args:
        data: 扁平字典。键可包含路径分隔符，例如 ``model.name``。
        sep: 键路径分隔符。

    Returns:
        dict[str, Any]: 还原后的嵌套字典。

    Raises:
        ValueError: 当路径冲突（同一路径既是值又是父节点）时抛出。

    Examples:
        >>> unflatten_dict({"model.name": "tiny", "model.layers": 12})
        {'model': {'name': 'tiny', 'layers': 12}}
    """
    nested: dict[str, Any] = {}
    for compound_key, value in data.items():
        parts = str(compound_key).split(sep)
        cursor: dict[str, Any] = nested
        for part in parts[:-1]:
            if part in cursor and not isinstance(cursor[part], dict):
                raise ValueError(f"Key conflict while unflattening: {compound_key}")
            cursor = cursor.setdefault(part, {})
        leaf = parts[-1]
        if leaf in cursor and isinstance(cursor[leaf], dict):
            raise ValueError(f"Key conflict while unflattening: {compound_key}")
        cursor[leaf] = value
    return nested


def deep_merge_dicts(
    base: Mapping[str, Any],
    override: Mapping[str, Any],
) -> dict[str, Any]:
    """递归合并两个字典并返回新字典。

    合并规则：
    1. 若同名键在两侧均为字典，则递归合并；
    2. 否则使用 ``override`` 覆盖 ``base``。

    Args:
        base: 基础字典。
        override: 覆盖字典。

    Returns:
        dict[str, Any]: 合并后的新字典（不会原地修改输入）。

    Examples:
        >>> deep_merge_dicts({"a": 1, "b": {"x": 1}}, {"b": {"y": 2}})
        {'a': 1, 'b': {'x': 1, 'y': 2}}
    """
    merged = copy.deepcopy(dict(base))
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, Mapping):
            merged[key] = deep_merge_dicts(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def dict_diff(left: Mapping[str, Any], right: Mapping[str, Any]) -> dict[str, Any]:
    """比较两个字典差异并返回结构化结果。

    Args:
        left: 左侧字典（通常视作“旧值”）。
        right: 右侧字典（通常视作“新值”）。

    Returns:
        dict[str, Any]:
            结构为 ``{"added": dict, "removed": dict, "changed": dict}``。
            其中 ``changed`` 的值格式为
            ``{"key.path": {"left": Any, "right": Any}}``。

    Examples:
        >>> dict_diff({"a": 1}, {"a": 2, "b": 3})["added"]
        {'b': 3}
    """
    left_flat = flatten_dict(left)
    right_flat = flatten_dict(right)

    left_keys = set(left_flat.keys())
    right_keys = set(right_flat.keys())

    added = {key: right_flat[key] for key in sorted(right_keys - left_keys)}
    removed = {key: left_flat[key] for key in sorted(left_keys - right_keys)}

    changed: dict[str, dict[str, Any]] = {}
    for key in sorted(left_keys & right_keys):
        if left_flat[key] != right_flat[key]:
            changed[key] = {"left": left_flat[key], "right": right_flat[key]}

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def sanitize_filename(name: str, replacement: str = "_", max_length: int = 128) -> str:
    """将字符串清洗为跨平台较安全的文件名。

    Args:
        name: 原始文件名文本。
        replacement: 非法字符替换符。
        max_length: 返回文件名最大长度（最小为 1）。

    Returns:
        str: 清洗后的文件名。

    Raises:
        ValueError: 当 ``max_length < 1`` 时抛出。

    Examples:
        >>> sanitize_filename("model:tiny/lr=1e-3")
        'model_tiny_lr=1e-3'
    """
    if max_length < 1:
        raise ValueError("max_length must be >= 1")

    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]+', replacement, name)
    cleaned = cleaned.strip().strip(".")
    cleaned = re.sub(r"\s+", replacement, cleaned)
    cleaned = re.sub(f"{re.escape(replacement)}+", replacement, cleaned)
    cleaned = cleaned[:max_length].strip(replacement)
    return cleaned or "untitled"


def build_run_name(
    config: Mapping[str, Any],
    keys: Sequence[str] | None = None,
    prefix: str = "run",
    max_length: int = 120,
    hash_length: int = 8,
) -> str:
    """根据配置生成稳定且可读的 run 名称。

    命名格式：``{prefix}_{k1}-{v1}_{k2}-{v2}_..._{hash}``。

    Args:
        config: 配置字典。
        keys: 参与命名的键序列；为 ``None`` 时按键名字典序全量使用。
        prefix: 名称前缀。
        max_length: 最大长度，超长会截断（仍保留末尾哈希）。
        hash_length: 配置哈希长度。

    Returns:
        str: 适合目录名/文件名的 run 名称。

    Examples:
        >>> build_run_name({"model": "tiny", "lr": 0.001}, keys=["model", "lr"])
        'run_model-tiny_lr-0.001_...'
    """
    selected_keys = list(keys) if keys is not None else sorted(config.keys())
    parts: list[str] = []
    for key in selected_keys:
        if key not in config:
            continue
        value = config[key]
        token = f"{key}-{value}"
        parts.append(sanitize_filename(token, max_length=40))

    digest = config_to_hash(dict(config), length=hash_length)
    name = "_".join([sanitize_filename(prefix, max_length=20), *parts, digest])
    if len(name) <= max_length:
        return name

    head_budget = max_length - hash_length - 1
    head = sanitize_filename(name[:head_budget], max_length=head_budget)
    return f"{head}_{digest}"


def split_batches(items: Sequence[Any], batch_size: int) -> list[list[Any]]:
    """按固定批大小切分序列。

    Args:
        items: 输入序列。
        batch_size: 单批大小，必须大于 0。

    Returns:
        list[list[Any]]: 批次列表。输入为空时返回空列表。

    Raises:
        ValueError: 当 ``batch_size <= 0`` 时抛出。

    Examples:
        >>> split_batches([1, 2, 3, 4, 5], 2)
        [[1, 2], [3, 4], [5]]
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be > 0")
    return [list(items[i : i + batch_size]) for i in range(0, len(items), batch_size)]


def write_text_atomic(
    file_path: str | Path,
    text: str,
    encoding: str = "utf-8",
) -> None:
    """以原子方式写入文本文件，避免写入中断导致半文件。

    Args:
        file_path: 目标文件路径。
        text: 文本内容。
        encoding: 文本编码。

    Returns:
        None

    Notes:
        实现方式为“同目录临时文件写入完成后 ``os.replace`` 覆盖目标”。
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding=encoding) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.remove(tmp_name)
        except OSError:
            pass
        raise


def save_json_atomic(
    data: dict[str, Any],
    file_path: str | Path,
    indent: int = 2,
) -> None:
    """以原子方式写入 JSON 文件。

    Args:
        data: 待保存字典。
        file_path: 输出路径。
        indent: JSON 缩进空格。

    Returns:
        None

    Examples:
        >>> save_json_atomic({"score": 0.9}, "./tmp/metrics.json")
    """
    payload = json.dumps(data, ensure_ascii=False, indent=indent, default=_json_default)
    write_text_atomic(file_path, payload, encoding="utf-8")


def append_jsonl(file_path: str | Path, record: dict[str, Any]) -> None:
    """向 JSONL 文件追加一条记录。

    Args:
        file_path: JSONL 文件路径。
        record: 单条记录字典。

    Returns:
        None

    Examples:
        >>> append_jsonl("./logs/events.jsonl", {"event": "start"})
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, default=_json_default)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_jsonl(file_path: str | Path, skip_invalid: bool = False) -> list[dict[str, Any]]:
    """读取 JSONL 文件为记录列表。

    Args:
        file_path: JSONL 文件路径。
        skip_invalid: 为 ``True`` 时跳过非法行；否则遇到非法行抛异常。

    Returns:
        list[dict[str, Any]]: 记录列表。不存在时返回空列表。

    Raises:
        json.JSONDecodeError: ``skip_invalid=False`` 且存在非法 JSON 行时抛出。
        ValueError: 存在顶层非 dict 的合法 JSON 行时抛出。
    """
    path = Path(file_path)
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError:
                if skip_invalid:
                    continue
                raise
            if not isinstance(item, dict):
                raise ValueError(f"JSONL line {line_no} is not an object.")
            records.append(item)
    return records


def retry_call(
    fn: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    wait_sec: float = 0.0,
    backoff: float = 1.0,
    jitter_sec: float = 0.0,
    retry_exceptions: tuple[type[BaseException], ...] = (Exception,),
    **kwargs: Any,
) -> Any:
    """按可配置策略重试执行函数。

    Args:
        fn: 目标函数。
        *args: 目标函数位置参数。
        max_attempts: 最大尝试次数（至少为 1）。
        wait_sec: 初始等待秒数。
        backoff: 每次失败后的等待放大倍率。
        jitter_sec: 每次等待的随机抖动上限（秒）。
        retry_exceptions: 触发重试的异常类型元组。
        **kwargs: 目标函数关键字参数。

    Returns:
        Any: 目标函数返回值。

    Raises:
        Exception: 超过最大重试次数后，抛出最后一次异常。
        ValueError: 配置参数非法时抛出。

    Examples:
        >>> state = {"n": 0}
        >>> def flaky():
        ...     state["n"] += 1
        ...     if state["n"] < 2:
        ...         raise RuntimeError("retry")
        ...     return "ok"
        >>> retry_call(flaky, max_attempts=3)
        'ok'
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    if wait_sec < 0 or backoff < 0 or jitter_sec < 0:
        raise ValueError("wait_sec/backoff/jitter_sec must be >= 0")

    delay = wait_sec
    last_error: BaseException | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except retry_exceptions as exc:
            last_error = exc
            if attempt >= max_attempts:
                break

            sleep_for = delay
            if jitter_sec > 0:
                sleep_for += random.uniform(0, jitter_sec)
            if sleep_for > 0:
                time.sleep(sleep_for)
            delay *= backoff

    if last_error is not None:
        raise last_error
    raise RuntimeError("retry_call reached an unexpected state.")


def pretty_print_namespace(args: Any, items_per_line: int = 3) -> None:
    """美观打印 Namespace。

    Args:
        args: ``argparse.Namespace``。
        items_per_line: 每行展示的键值对数量。

    Returns:
        None
    """
    args_dict = vars(args)
    if not args_dict:
        print("No arguments to print.")
        return
    pretty_print_dict(args_dict, items_per_line)


def pretty_print_dict(d: dict[str, Any], items_per_line: int = 3) -> None:
    """美观打印字典。

    Args:
        d: 目标字典。
        items_per_line: 每行展示的键值对数量。

    Returns:
        None
    """
    if not d:
        print("No items in dictionary to print.")
        return

    key_width = max(len(str(k)) for k in d.keys()) + 4
    val_width = max(len(str(v)) for v in d.values()) + 4
    items = sorted(d.items(), key=lambda item: str(item[0]))

    for i in range(0, len(items), items_per_line):
        line = ""
        for j in range(items_per_line):
            if i + j < len(items):
                key, value = items[i + j]
                line += f"| \033[92m {key:<{key_width}} \033[94m{str(value):>{val_width}} \033[0m"
        line += "|"
        print(line)


def create_dir(path: str | Path) -> None:
    """递归创建目录（已存在则忽略）。

    Args:
        path: 目录路径。

    Returns:
        None
    """
    os.makedirs(path, exist_ok=True)


def delete_dir(path: str | Path) -> None:
    """删除目录及其全部内容。

    Args:
        path: 目标目录路径。

    Returns:
        None
    """
    target = Path(path)
    if target.exists() and target.is_dir():
        shutil.rmtree(target)
        print(f"Deleted directory: {target}")


def get_subdirectories(path: str | Path) -> list[pathlib.Path]:
    """获取路径下的一级子目录列表。

    Args:
        path: 目标路径。

    Returns:
        list[pathlib.Path]: 一级子目录列表；不存在时返回空列表。
    """
    p = pathlib.Path(path)
    if not p.exists() or not p.is_dir():
        return []
    return [folder for folder in p.iterdir() if folder.is_dir()]


def get_file_creation_time(file_path: str | Path) -> str:
    """获取文件创建时间字符串。

    Args:
        file_path: 文件路径。

    Returns:
        str: 格式为 ``YYYY/MM/DD-HH:MM:SS``。
    """
    path = pathlib.Path(file_path)
    timestamp = path.stat().st_ctime
    creation_time = datetime.fromtimestamp(timestamp)
    return creation_time.strftime("%Y/%m/%d-%H:%M:%S")
