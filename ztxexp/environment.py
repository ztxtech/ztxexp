"""
Experiment Environment Setup
============================

This module provides utilities for setting up the experiment environment,
including GPU initialization, random seed setting, and process priority management.

Functions:
    init_torch_env: Initializes the PyTorch environment with specified parameters.
    set_process_priority: Sets the priority of the current process.
"""
import os
import random

import numpy as np
import psutil
import torch


def init_torch_env(
        seed: int = 3407,
        use_gpu: bool = True,
        gpu_id: int = 0,
        deterministic: bool = False,
        benchmark: bool = False
):
    """
    Initializes the environment for reproducible deep learning experiments.

    Args:
        seed (int): The random seed.
        use_gpu (bool): Whether to use GPU if available.
        gpu_id (int): The GPU ID to use.
        deterministic (bool): Whether to use deterministic algorithms.
        benchmark (bool): Whether to let cuDNN find the best algorithm.
    """
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
    else:
        print("Using CPU")
        return torch.device("cpu")


def set_process_priority(priority: str = 'high'):
    """
    Set the priority of the current process.
    'high', 'normal', 'low'
    """
    p = psutil.Process(os.getpid())
    try:
        if priority == 'high':
            p.nice(psutil.HIGH_PRIORITY_CLASS)
        elif priority == 'low':
            p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        else:
            p.nice(psutil.NORMAL_PRIORITY_CLASS)
    except AttributeError:
        # For non-Windows systems
        # Lower nice value means higher priority
        if priority == 'high':
            p.nice(-10)
        elif priority == 'low':
            p.nice(10)
        else:
            p.nice(0)
