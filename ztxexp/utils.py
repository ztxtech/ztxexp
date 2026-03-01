"""General utilities for ztxexp."""

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
    try:
        return __import__(module_name)
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            f"Optional dependency '{module_name}' is required for this function. "
            f"Install with: pip install ztxexp[{extra_name}]"
        ) from exc


# --- Path & System Management ---

def add_to_sys_path(path: str | Path) -> None:
    """Adds a directory to the Python system path if it is not already there."""
    abs_path = str(Path(path).resolve())
    if abs_path not in sys.path:
        sys.path.insert(0, abs_path)
        print(f"Added '{abs_path}' to system path.")


# --- Logging ---

def setup_logger(name: str, log_file: str | Path, level: int = logging.INFO) -> logging.Logger:
    """Sets up a logger that writes to both a file and the console."""
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


# --- Serialization ---

def save_json(data: dict[str, Any], file_path: str | Path, indent: int = 2) -> None:
    """Saves a dictionary to JSON."""
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=indent, default=_json_default)


def load_json(file_path: str | Path) -> dict[str, Any] | None:
    """Loads JSON into dict. Returns None when file is missing."""
    path = Path(file_path)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return data
    return None


def save_dill(obj: object, file_path: str | Path) -> None:
    """Serializes and saves an object using dill."""
    dill = _require_dependency("dill", "core")
    with open(file_path, "wb") as handle:
        dill.dump(obj, handle)


def load_dill(file_path: str | Path) -> object:
    """Loads and deserializes an object using dill."""
    dill = _require_dependency("dill", "core")
    with open(file_path, "rb") as handle:
        return dill.load(handle)


def save_torch_model(model, optimizer, epoch: int, path: str | Path) -> None:
    """Saves a torch model checkpoint."""
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
    """Loads a torch model checkpoint."""
    torch = _require_dependency("torch", "torch")
    checkpoint = torch.load(path, map_location="cpu")
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer and checkpoint.get("optimizer_state_dict"):
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    epoch = checkpoint.get("epoch", 0)
    return model, optimizer, epoch


# --- Timing and Performance ---

@contextmanager
def timer(name: str, logger: logging.Logger | None = None):
    """Times a code block and logs/prints elapsed seconds."""
    t0 = time.time()
    yield
    elapsed = time.time() - t0
    message = f"[{name}] done in {elapsed:.4f}s"
    if logger:
        logger.info(message)
    else:
        print(message)


def format_time_delta(seconds: float) -> str:
    """Formats seconds into H/M/S."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}h {m}m {s}s"


def get_memory_usage() -> str:
    """Returns the memory usage of the current process in MB."""
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return f"{mem_info.rss / 1024 ** 2:.2f} MB"


# --- Hashing and Reproducibility ---

def config_to_hash(config: dict[str, Any], length: int = 8) -> str:
    """Creates a deterministic hash from a configuration dictionary."""
    sorted_config_str = json.dumps(config, sort_keys=True, default=_json_default)
    hash_object = hashlib.sha256(sorted_config_str.encode("utf-8"))
    return hash_object.hexdigest()[:length]


# --- Display and Formatting ---

def pretty_print_namespace(args, items_per_line: int = 3) -> None:
    """Prints argparse.Namespace in a formatted and colorful way."""
    args_dict = vars(args)
    if not args_dict:
        print("No arguments to print.")
        return
    pretty_print_dict(args_dict, items_per_line)


def pretty_print_dict(d: dict[str, Any], items_per_line: int = 3) -> None:
    """Prints a dictionary in a formatted and colorful way."""
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


# --- Directory and File Operations ---

def create_dir(path: str | Path) -> None:
    """Creates a directory if it does not exist."""
    os.makedirs(path, exist_ok=True)


def delete_dir(path: str | Path) -> None:
    """Deletes a directory and all its contents."""
    target = Path(path)
    if target.exists() and target.is_dir():
        shutil.rmtree(target)
        print(f"Deleted directory: {target}")


def get_subdirectories(path: str | Path) -> list[pathlib.Path]:
    """Returns all immediate subdirectories under path."""
    p = pathlib.Path(path)
    if not p.exists() or not p.is_dir():
        return []
    return [folder for folder in p.iterdir() if folder.is_dir()]


def get_file_creation_time(file_path: str | Path) -> str:
    """Gets formatted creation time for a file."""
    path = pathlib.Path(file_path)
    timestamp = path.stat().st_ctime
    creation_time = datetime.fromtimestamp(timestamp)
    return creation_time.strftime("%Y/%m/%d-%H:%M:%S")
