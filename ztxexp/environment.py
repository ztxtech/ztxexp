"""Environment helpers for deep learning experiments."""

from __future__ import annotations

import os
import random

import numpy as np
import psutil


def _require_torch():
    try:
        import torch

        return torch
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "PyTorch is required for init_torch_env. Install with: pip install ztxexp[torch]"
        ) from exc


def init_torch_env(
    seed: int = 3407,
    use_gpu: bool = True,
    gpu_id: int = 0,
    deterministic: bool = False,
    benchmark: bool = False,
):
    """Initializes deterministic state and optional CUDA settings."""
    torch = _require_torch()

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    if torch.cuda.is_available() and use_gpu:
        torch.cuda.manual_seed_all(seed)
        torch.cuda.set_device(gpu_id)
        torch.backends.cudnn.deterministic = deterministic
        torch.backends.cudnn.benchmark = benchmark
        print(f"Using GPU: {gpu_id}")
        return torch.device(f"cuda:{gpu_id}")

    print("Using CPU")
    return torch.device("cpu")


def set_process_priority(priority: str = "high") -> None:
    """Sets process priority. Valid values: high/normal/low."""
    process = psutil.Process(os.getpid())
    selected = priority.strip().lower()

    try:
        if os.name == "nt":
            if selected == "high":
                process.nice(psutil.HIGH_PRIORITY_CLASS)
            elif selected == "low":
                process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            else:
                process.nice(psutil.NORMAL_PRIORITY_CLASS)
        else:
            if selected == "high":
                process.nice(-10)
            elif selected == "low":
                process.nice(10)
            else:
                process.nice(0)
    except (psutil.AccessDenied, PermissionError) as exc:  # pragma: no cover
        raise PermissionError(
            "Insufficient permission to change process priority. "
            "Try running with elevated privileges or use 'normal'."
        ) from exc
