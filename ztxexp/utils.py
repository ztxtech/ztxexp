"""通用工具函数集合。

该模块被 manager/runner/analyzer 等核心组件复用，设计原则：
1. 纯工具、低耦合；
2. 尽量无全局副作用；
3. 对可选依赖提供明确错误提示。
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import pathlib
import shutil
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

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


def _require_dependency(module_name: str, extra_name: str):
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


def save_torch_model(model, optimizer, epoch: int, path: str | Path) -> None:
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


def load_torch_model(model, optimizer, path: str | Path):
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
def timer(name: str, logger: logging.Logger | None = None):
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


def pretty_print_namespace(args, items_per_line: int = 3) -> None:
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
