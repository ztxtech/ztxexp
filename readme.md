# ztxexp

[![GitHub Stars](https://img.shields.io/github/stars/ztxtech/ztxexp?style=social)](https://github.com/ztxtech/ztxexp/)
[![PyPI version](https://badge.fury.io/py/ztxexp.svg)](https://badge.fury.io/py/ztxexp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/ztxexp.svg)](https://pypi.org/project/ztxexp)

**ztxexp** (ZTX-Experiment)
是一个轻量级、零依赖（除Python标准库外）且功能强大的Python工具库，旨在将您从繁琐的计算实验管理中解放出来。它特别适用于机器学习、深度学习和任何需要进行大量参数搜索与结果分析的研究场景。

由 [**ztxtech**](https://github.com/ztxtech) 开发，ztxexp 将实验设计的全流程——**配置生成、增量运行、结果分析、目录清理**
——封装在一套优雅流畅的API中。

## 核心功能 ✨

* **🚀 流畅的参数配置**: 使用链式API轻松定义参数空间，支持网格搜索 (`Grid Search`) 和独立变体 (`Variants`)。
* **🔧 自定义逻辑**: 通过添加自定义的修改器和过滤器函数，实现任意复杂的参数调整和筛选逻辑。
* **💡 智能防重运行**: 自动检测已完成的实验，避免重复计算，节省宝贵的计算时间和资源。
* **⚡️ 灵活的执行引擎**: 支持多种实验执行模式，包括**顺序执行**、**并行执行** (`ProcessPoolExecutor` 或 `joblib`)。
* **📊 强大的结果分析**: 一键将所有分散的实验结果聚合到 Pandas DataFrame 中，并支持生成多维数据透视表（Pivot Table）与排名。
* **🧹 安全的目录清理**: 提供安全的 `dry_run` 模式和交互式确认，帮助你轻松删除未成功或不符合预期的实验结果。
* **🛠️ 丰富的工具集**: 内置一个不断丰富的 `utils.py` 模块，提供日志设置、代码计时、模型保存、路径管理等高频实用工具。

## 安装

```bash
pip install ztxexp
```

-----

## 核心工作流

`ztxexp` 的设计遵循一个简单直观的三段式工作流：

1. **管理 (Manage)**: 使用 `ztxexp.ExpManager` 定义和生成所有需要运行的实验配置。
2. **运行 (Run)**: 使用 `ztxexp.ExpRunner` 来执行这些配置，支持并行化和断点续跑。
3. **分析 (Analyze)**: 使用 `ztxexp.ResultAnalyzer` 来聚合结果、生成报告以及清理工作目录。

-----

## 用法示例

为了帮助你快速上手，我们在项目中提供了几个可直接运行的示例脚本。建议你亲自运行它们，以更好地理解库的功能。

* **`main_run_experiments.py`**: **（核心示例）** 展示了如何使用 `ExpManager` 的链式API组合网格搜索、变体、修改器和过滤器来生成复杂的实验配置，并使用
  `ExpRunner` 进行并行执行。这是理解本库强大之处的最佳起点。

  ```python
  # 节选自 main_run_experiments.py
  configs_to_run = (
      manager.add_grid_search(GRID_SPACE)
             .add_variants(VARIANT_SPACE)
             .add_modifier(modifier_func)
             .add_filter(filter_func)
             .filter_completed('./results_demo')
             .get_configs()
  )
  ```

* **`main_analyze_results.py`**: 演示了在实验运行后，如何使用 `ResultAnalyzer` 将所有成功运行的结果汇总到CSV文件，并创建一个带排名的精美Excel数据透视表。

* **`main_cleanup.py`**: 专注于目录维护。它展示了如何使用 `clean_results` 方法安全地、有选择性地删除那些失败的、未完成的、或者结果不符合预期的实验文件夹。

* **`main_utils_demo.py`**: 展示了 `ztxexp.utils` 模块的威力。即使不使用完整的 Manager/Runner
  工作流，你也可以在任何Python脚本中单独使用这些方便的工具函数，如日志记录器、代码计时器、PyTorch模型保存等。

-----

## API核心：自定义函数详解

`ztxexp` 的强大之处在于其高度的可定制性。你需要提供几个关键的自定义函数，下面是它们的详细“接口契约”。

### 1\. 实验主函数 (`exp_function`)

这是你的核心业务逻辑所在，由 `ExpRunner` 负责调用。

* **签名**: `def my_experiment(args: argparse.Namespace):`
* **参数**:
    * `args`: 一个 `Namespace` 对象，包含了本次运行所需的所有配置。`ExpRunner` 会自动向其添加两个额外的属性：
        * `args.setting`: 本次运行的唯一标识符（例如 `20250803_202020_a1b2c3`）。
        * `args.setting_path`: 本次运行的专属结果目录 (`Path` 对象)，你可以向其中保存任何文件。
* **职责**:
    1. 执行你的实验代码（模型训练、数据处理等）。
    2. **必须自己保存结果**。例如，将指标保存到 `args.setting_path / 'results.json'`，将模型权重保存到
       `args.setting_path / 'model.pth'`。
* **返回值**: 无需返回值。`ExpRunner` 通过检查 `_SUCCESS` 标记文件（在函数成功返回后自动创建）来判断成功与否。

### 2\. 参数修改器 (`modifier_func`)

用于在生成最终配置列表前，对参数进行动态调整。

* **签名**: `def my_modifier(args: argparse.Namespace) -> argparse.Namespace:`
* **参数**:
    * `args`: 一个待处理的 `Namespace` 配置对象。
* **职责**: 根据已有参数修改`args`对象。例如：`if args.model == 'A': args.layers = 12`。
* **返回值**: **必须**返回修改后的 `args` 对象。

### 3\. 参数过滤器 (`filter_func`)

用于在生成最终配置列表前，剔除无效或不想运行的参数组合。

* **签名**: `def my_filter(args: argparse.Namespace) -> bool:`

* **参数**:

    * `args`: 一个待检查的 `Namespace` 配置对象。

* **职责**: 根据一组规则判断该配置是否有效。

* **返回值**: **必须**返回一个布尔值：

    * `True`：保留这个配置。
    * `False`：从待运行列表中**剔除**这个配置。

* **最佳实践**: 为了防止因参数缺失而导致程序崩溃，请始终使用 `.get()` 方法来安全地访问 `args` 中的属性。

  ```python
  # 安全的写法
  def my_safe_filter(args):
      # 如果 'lr' 存在且小于 0.001，则保留
      if args_dict := vars(args):
           if args_dict.get('lr', 999) < 0.001:
               return True
      return False

  # 不安全的写法 (如果 'lr' 缺失会引发 AttributeError)
  # def my_unsafe_filter(args):
  #     return args.lr < 0.001
  ```

### 4\. 目录清理过滤器 (`filter_func` for `clean_results`)

用于 `ResultAnalyzer.clean_results` 方法，以编程方式决定哪些文件夹需要被删除。

* **签名**: `def my_cleanup_filter(config_dict: dict) -> bool:`

* **参数**:

    * `config_dict`: 从一个 `args.json` 文件中加载而来的字典。

* **职责**: 判断这个配置是否符合被删除的条件。

* **返回值**: **必须**返回一个布尔值：

    * `True`：**标记此文件夹为待删除**。
    * `False`：保留此文件夹。

* **最佳实践**: 同样地，请务必使用 `.get()` 来处理可能缺失的键。

  ```python
  # 安全的写法：删除所有准确率低于 0.5 的实验
  def cleanup_low_accuracy(config):
      # 如果 'accuracy' 键不存在，.get 返回 1.0，条件不成立，不会被删除
      return config.get('accuracy', 1.0) < 0.5
  ```

## 贡献

欢迎任何形式的贡献！如果你有好的想法或发现了Bug，请随时在 [GitHub Issues](https://www.google.com/search?q=https://github.com/ztxtech/ztxtech-exp/issues)
中提出，或者直接提交一个 Pull Request。

## 许可证

该项目采用 [MIT License](https://opensource.org/licenses/MIT) 授权。