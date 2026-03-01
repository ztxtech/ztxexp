"""实验运行环境相关工具。

本模块用于：
1. 初始化深度学习实验的随机性与设备；
2. 设置当前进程优先级。
"""

from __future__ import annotations

import os
import random
from typing import Any

import numpy as np
import psutil


def _require_torch() -> Any:
    """按需导入 torch。

    Returns:
        module: 导入后的 torch 模块对象。

    Raises:
        ImportError: 当环境中未安装 torch 时抛出，并给出安装提示。
    """
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
) -> Any:
    """初始化 PyTorch 实验环境。

    Args:
        seed: 全局随机种子（Python/NumPy/Torch 同步设置）。
        use_gpu: 是否优先使用 GPU。
        gpu_id: 当启用 GPU 时使用的设备 ID。
        deterministic: 是否启用 cuDNN 确定性模式。
        benchmark: 是否启用 cuDNN benchmark 自动搜索最优算法。

    Returns:
        torch.device: 最终使用的设备对象（CPU 或 CUDA）。

    Raises:
        ImportError: 未安装 torch 时抛出。

    Examples:
        >>> device = init_torch_env(seed=42, use_gpu=False)
        >>> str(device)
        'cpu'
    """
    # 延迟导入 torch，避免非 torch 用户在导入包时失败。
    torch = _require_torch()

    # 设置三套随机种子，提升实验复现稳定性。
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    # GPU 路径：设置设备与 cuDNN 行为。
    if torch.cuda.is_available() and use_gpu:
        torch.cuda.manual_seed_all(seed)
        torch.cuda.set_device(gpu_id)
        torch.backends.cudnn.deterministic = deterministic
        torch.backends.cudnn.benchmark = benchmark
        print(f"Using GPU: {gpu_id}")
        return torch.device(f"cuda:{gpu_id}")

    # CPU 回退路径。
    print("Using CPU")
    return torch.device("cpu")


def set_process_priority(priority: str = "high") -> None:
    """设置当前进程优先级。

    Args:
        priority: 优先级级别，可选值为 ``high`` / ``normal`` / ``low``。

    Returns:
        None

    Raises:
        PermissionError: 当前权限不足，无法修改进程优先级。

    Examples:
        >>> set_process_priority("normal")
    """
    process = psutil.Process(os.getpid())
    selected = priority.strip().lower()

    try:
        # Windows 使用优先级类；类 Unix 使用 nice 值。
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
