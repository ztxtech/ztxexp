import time
from argparse import Namespace

import torch

from ztxexp import utils


def experiment_entrypoint(args: Namespace):
    """
    一个通用的实验函数，用于所有示例。
    - 模拟不同的运行时间。
    - 当学习率 > 0.05 时，模拟实验失败。
    - 保存准确率、损失和耗时作为结果。
    """
    start_time = time.time()
    print(f"🚀 Running experiment: {args.setting}")
    print(f"   - Config: Model={args.model}, LR={args.lr}, Dataset={args.dataset}")

    # 模拟一个会失败的条件
    if args.lr > 0.05:
        time.sleep(1)
        raise ValueError(f"Learning rate {args.lr} is too high, simulating a crash!")

    # 模拟基于参数的耗时
    if args.model == 'Transformer':
        time.sleep(3)  # Transformer模型耗时更长
    else:
        time.sleep(1)

    # 模拟产出结果
    accuracy = 1.0 - (args.lr * 10) - (0.1 if args.model == 'Transformer' else 0.2) + torch.rand(1).item() * 0.1
    loss = (1 - accuracy) * 2.0

    results = {
        "accuracy": round(accuracy, 4),
        "loss": round(loss, 4),
        "time_taken_sec": round(time.time() - start_time, 2)
    }

    # 保存结果到 results.json
    utils.save_json(results, args.setting_path / 'results.json')
    print(f"   - ✅ Results saved. Accuracy: {results['accuracy']:.4f}")
