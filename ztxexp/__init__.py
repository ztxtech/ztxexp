"""ztxexp 包级导出。

该模块定义用户最常用的导入入口，例如：

    from ztxexp import ExperimentPipeline, ResultAnalyzer
"""

from ztxexp.analyzer import ResultAnalyzer
from ztxexp.environment import init_torch_env, set_process_priority
from ztxexp.manager import ExpManager
from ztxexp.pipeline import ExperimentPipeline
from ztxexp.runner import ExpRunner, SkipRun
from ztxexp.tracking import JsonlTracker, MlflowTracker, Tracker, WandbTracker
from ztxexp.types import MetricEvent, RunContext, RunMetadata, RunSummary

# from ztxexp import * 的公开符号集合。
__all__ = [
    "ExpManager",
    "ExpRunner",
    "ResultAnalyzer",
    "ExperimentPipeline",
    "RunContext",
    "RunMetadata",
    "MetricEvent",
    "RunSummary",
    "SkipRun",
    "Tracker",
    "JsonlTracker",
    "MlflowTracker",
    "WandbTracker",
    "init_torch_env",
    "set_process_priority",
]

# 包版本号，供运行时查询。
__version__ = "1.0.2"
