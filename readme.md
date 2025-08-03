# ztxexp

[](https://www.google.com/search?q=https://badge.fury.io/py/ztxexp)
[](https://opensource.org/licenses/MIT)
[](https://www.google.com/search?q=https://pypi.org/project/ztxexp)

**ztxexp** (ZTX-Experiment)
是一个轻量级、零依赖（除Python标准库外）且功能强大的Python工具库，旨在将您从繁琐的计算实验管理中解放出来。它特别适用于机器学习、深度学习和任何需要进行大量参数搜索与结果分析的研究场景。

由 [**ztxtech**](https://github.com/ztxtech) 开发，ztxexp 将实验设计的全流程——**配置生成、增量运行、结果分析、目录清理**
——封装在一套优雅流畅的API中。

## 核心功能 ✨

* **🚀 流畅的参数配置**: 使用链式API轻松定义参数空间，支持网格搜索 (`Grid Search`) 和独立变体 (`Variants`)。
* **🔧 自定义逻辑**: 通过添加自定义的修改器和过滤器函数，实现任意复杂的参数调整和筛选逻辑。
* **💡 智能防重运行**: 自动检测已完成的实验，避免重复计算，节省宝贵的计算时间和资源。
* **⚡️ 灵活的执行引擎**: 支持多种实验执行模式，包括**顺序执行**、**并行执行** (`ProcessPoolExecutor` 或 `joblib`)
  ，以及自定义的动态调度策略。
* **📊 强大的结果分析**: 一键将所有分散的实验结果聚合到 Pandas DataFrame 中，并支持生成多维数据透视表（Pivot Table）与排名。
* **🧹 安全的目录清理**: 提供安全的 `dry_run` 模式和交互式确认，帮助你轻松删除未成功或不符合预期的实验结果。
* **🛠️ 丰富的工具集**: 内置一个不断丰富的 `utils.py` 模块，提供日志设置、代码计时、模型保存、路径管理等高频实用工具。

## 安装

```bash
pip install ztxexp
```

*(注意: 包名 `ztxexp` 是一个示例，请替换为你最终在PyPI上发布的名字，例如 `ztxtech-exp`)*

-----

## 快速入门 🚀

让我们通过一个三步走的例子来感受 `ztxexp` 的魅力。

### 第1步: 定义你的实验核心逻辑

这是你自己的业务代码，ztxexp 不会侵入其中。你只需要把它封装成一个接收 `args` 对象的函数。

```python
# my_experiment.py
import time
import torch
from argparse import Namespace
from ztxexp import utils


def experiment_entrypoint(args: Namespace):
    """
    这是你的实验主函数。
    ztxexp.Runner 会调用它，并传入包含了所有配置和路径信息的args。
    """
    print(f"🚀 Running experiment: {args.setting}")
    print(f"   - Model: {args.model}, LR: {args.lr}, Dataset: {args.dataset}")

    # 你的核心代码...
    time.sleep(1)  # 模拟训练
    results = {
        "accuracy": torch.rand(1).item(),
        "loss": (1 - args.lr) * torch.rand(1).item()
    }

    # 将结果保存到ztxexp为你创建的目录中
    utils.save_json(results, args.setting_path / 'results.json')
    print(f"   - ✅ Results saved to {args.setting_path}")
```

### 第2步: 定义参数空间

创建一个文件来管理你的命令行参数和搜索空间。

```python
# config.py
import argparse


def get_base_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='ResNet', help='Model architecture')
    parser.add_argument('--epochs', type=int, default=20, help='Number of epochs')
    parser.add_argument('--use_gpu', action='store_true', default=False, help='Whether to use GPU')
    # ... 其他基本参数
    return parser.parse_args()


# 定义网格搜索空间
GRID_SPACE = {
    'lr': [0.01, 0.005],
    'batch_size': [32, 64]
}

# 定义独立变体空间
VARIANT_SPACE = {
    'dataset': ['CIFAR10', 'ImageNet-Subset']
}
```

### 第3步: 编排、运行和分析！

这是你的主脚本，它将所有部分串联起来。

```python
# main.py
import ztxexp
from config import get_base_args, GRID_SPACE, VARIANT_SPACE
from my_experiment import experiment_entrypoint

# --- 1. 管理 (Manage): 定义实验组合 ---
print("=" * 20 + " 1. Managing Configurations " + "=" * 20)
base_args = get_base_args()
manager = ztxexp.ExpManager(base_args)

configs_to_run = (
    manager.add_grid_search(GRID_SPACE)  # 首先进行网格搜索
    .add_variants(VARIANT_SPACE)  # 然后为每个组合添加变体
    .shuffle()  # 打乱实验顺序
    .filter_completed('./my_results')  # 过滤掉已经跑完的实验
    .get_configs()  # 获取最终要运行的配置列表
)

# --- 2. 运行 (Run): 执行实验 ---
print("\n" + "=" * 20 + " 2. Running Experiments " + "=" * 20)
if not configs_to_run:
    print("🎉 All experiments are already completed!")
else:
    ztxexp.init_torch_env(use_gpu=base_args.use_gpu)  # 初始化环境
    runner = ztxexp.ExpRunner(
        configs=configs_to_run,
        exp_function=experiment_entrypoint,
        results_root='./my_results'
    )
    # 使用joblib并行运行，设置8个工作进程
    runner.run(execution_mode='joblib', num_workers=8)

# --- 3. 分析 (Analyze): 聚合与清理结果 ---
print("\n" + "=" * 20 + " 3. Analyzing Results " + "=" * 20)
analyzer = ztxexp.ResultAnalyzer(results_path='./my_results')

# 将所有成功实验的结果聚合到CSV
analyzer.to_csv(output_path='./my_results/summary.csv', sort_by=['dataset', 'lr'])
print("\n📋 Summary CSV has been generated.")

# 生成数据透视表，并按accuracy排名
df = analyzer.to_dataframe()
if not df.empty:
    analyzer.to_pivot_excel(
        output_path='./my_results/pivot_summary.xlsx',
        df=df,
        index_cols=['dataset', 'batch_size'],
        column_cols=['lr'],
        value_cols=['accuracy']
    )
    print("📊 Pivot table has been generated.")

# 清理不完整（失败）的实验文件夹 (默认使用_SUCCESS标记)
print("\n🧹 Cleaning up incomplete runs (Dry Run)...")
analyzer.clean_results(dry_run=True)
```

-----

## 贡献

欢迎任何形式的贡献！如果你有好的想法或发现了Bug，请随时在 [GitHub Issues](https://www.google.com/search?q=https://github.com/ztxtech/ztxexp/issues)
中提出，或者直接提交一个 Pull Request。

## 许可证

该项目采用 [MIT License](https://opensource.org/licenses/MIT) 授权。