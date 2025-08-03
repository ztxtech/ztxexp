# ztxexp/utils.py

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

import dill
import psutil
import torch


# --- Path & System Management ---

def add_to_sys_path(path: str):
    """
    Adds a directory to the Python system path if it's not already there.

    Args:
        path (str): The path to the directory to be added.
    """
    abs_path = str(Path(path).resolve())
    if abs_path not in sys.path:
        sys.path.insert(0, abs_path)
        print(f"Added '{abs_path}' to system path.")


# --- Logging ---

def setup_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """
    Sets up a logger that writes to both a file and the console.

    Args:
        name (str): The name of the logger.
        log_file (str): The path to the log file.
        level: The logging level (e.g., logging.INFO, logging.DEBUG).

    Returns:
        logging.Logger: The configured logger instance.
    """
    # Ensure log directory exists
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # Console handler
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid adding handlers multiple times
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return logger


# --- Serialization ---

def save_json(data: dict, file_path: str, indent: int = 4):
    """Saves a dictionary to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_json(file_path: str) -> dict | None:
    """Loads a dictionary from a JSON file."""
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_dill(obj: object, file_path: str):
    """Serializes and saves a Python object using dill."""
    with open(file_path, 'wb') as f:
        dill.dump(obj, f)


def load_dill(file_path: str) -> object:
    """Loads and deserializes a Python object using dill."""
    with open(file_path, 'rb') as f:
        return dill.load(f)


def save_torch_model(model: torch.nn.Module, optimizer: torch.optim.Optimizer, epoch: int, path: str):
    """Saves a PyTorch model checkpoint."""
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
    }, path)


def load_torch_model(model: torch.nn.Module, optimizer: torch.optim.Optimizer, path: str) -> tuple:
    """Loads a PyTorch model checkpoint."""
    checkpoint = torch.load(path)
    model.load_state_dict(checkpoint['model_state_dict'])
    if optimizer:
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    epoch = checkpoint['epoch']
    return model, optimizer, epoch


# --- Timing and Performance ---

@contextmanager
def timer(name: str, logger: logging.Logger = None):
    """
    A context manager to time a block of code.

    Args:
        name (str): The name of the timed block.
        logger (logging.Logger, optional): If provided, logs the time.
    """
    t0 = time.time()
    yield
    elapsed = time.time() - t0
    message = f"[{name}] done in {elapsed:.4f} s"
    if logger:
        logger.info(message)
    else:
        print(message)


def format_time_delta(seconds: float) -> str:
    """Formats a duration in seconds into a human-readable string (H, M, S)."""
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

def config_to_hash(config: dict, length: int = 8) -> str:
    """
    Creates a deterministic hash from a configuration dictionary.

    Args:
        config (dict): The configuration dictionary.
        length (int): The desired length of the hash string.

    Returns:
        str: A truncated SHA256 hash.
    """
    # Sort the dictionary to ensure order doesn't affect the hash
    sorted_config_str = json.dumps(config, sort_keys=True)
    hash_object = hashlib.sha256(sorted_config_str.encode('utf-8'))
    return hash_object.hexdigest()[:length]


# --- Display and Formatting ---

def pretty_print_namespace(args, items_per_line: int = 3):
    """Prints argparse.Namespace in a formatted and colorful way."""
    args_dict = vars(args)
    if not args_dict:
        print("No arguments to print.")
        return

    pretty_print_dict(args_dict, items_per_line)


def pretty_print_dict(d: dict, items_per_line: int = 3):
    """Prints a dictionary in a formatted and colorful way."""
    if not d:
        print("No items in dictionary to print.")
        return

    key_width = max([len(k) for k in d.keys()]) + 4
    val_width = max([len(str(v)) for v in d.values()]) + 4

    items = sorted(d.items(), key=lambda x: x[0])

    for i in range(0, len(items), items_per_line):
        line = ""
        for j in range(items_per_line):
            if i + j < len(items):
                key, value = items[i + j]
                line += f"| \033[92m {key:<{key_width}} \033[94m{str(value):>{val_width}} \033[0m"
        line += "|"
        print(line)


# --- Directory and File Operations ---

def create_dir(path: str):
    """
    Create a directory if it does not exist.
    """
    os.makedirs(path, exist_ok=True)


def delete_dir(path: str):
    """
    Delete a directory and all its contents.
    """
    if os.path.exists(path) and os.path.isdir(path):
        shutil.rmtree(path)
        print(f'Deleted directory: {path}')


def get_subdirectories(path: str) -> list[pathlib.Path]:
    """
    Get all subdirectories in a given path.
    """
    p = pathlib.Path(path)
    if not p.exists() or not p.is_dir():
        return []
    return [folder for folder in p.iterdir() if folder.is_dir()]


def get_file_creation_time(file_path: str) -> str:
    """
    Get the creation time of a file formatted as a string.
    """
    path = pathlib.Path(file_path)
    timestamp = path.stat().st_ctime
    creation_time = datetime.fromtimestamp(timestamp)
    return creation_time.strftime("%Y/%m/%d-%H:%M:%S")
