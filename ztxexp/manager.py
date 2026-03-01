"""实验配置管理器。

本模块负责“配置生成与筛选”，不负责执行实验。
核心能力：
1. 网格搜索扩展（grid）；
2. 独立变体扩展（variants）；
3. 配置修改与过滤（modify/where）；
4. 排除已完成配置（exclude_completed）。
"""

from __future__ import annotations

import argparse
import copy
import itertools
import random
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from ztxexp import utils
from ztxexp.constants import RUN_SCHEMA_VERSION, RUN_STATUS_SUCCEEDED

# 统一配置类型，便于阅读和类型推断。
ConfigDict = dict[str, Any]

# 修改器：返回新字典，或原地修改后返回 None。
Modifier = Callable[[ConfigDict], ConfigDict | None]

# 过滤器：True 保留，False 丢弃。
Predicate = Callable[[ConfigDict], bool]


def _namespace_to_dict(value: argparse.Namespace | Mapping[str, Any]) -> ConfigDict:
    """将 Namespace/Mapping 统一转换为普通字典。

    Args:
        value: ``argparse.Namespace`` 或任意映射类型。

    Returns:
        dict[str, Any]: 拷贝后的普通字典。

    Examples:
        >>> import argparse
        >>> ns = argparse.Namespace(lr=0.01)
        >>> _namespace_to_dict(ns)
        {'lr': 0.01}
    """
    if isinstance(value, argparse.Namespace):
        return vars(value).copy()
    return dict(value)


class ExpManager:
    """实验配置构建器。

    该类维护一条配置流水线：
    ``grid -> variants -> modify -> where -> exclude_completed -> shuffle``。

    Args:
        base_config: 基础配置。可传 ``Namespace``、``dict`` 或 ``None``。

    Examples:
        >>> manager = (
        ...     ExpManager({"seed": 42})
        ...     .grid({"lr": [1e-3, 1e-2]})
        ...     .variants([{"model": "tiny"}, {"model": "base"}])
        ...     .where(lambda c: c["lr"] < 0.02)
        ... )
        >>> len(manager.build())
        4
    """

    def __init__(self, base_config: argparse.Namespace | Mapping[str, Any] | None = None):
        base = {} if base_config is None else _namespace_to_dict(base_config)
        self._configs: list[ConfigDict] = [base]
        self._modifiers: list[Modifier] = []
        self._predicates: list[Predicate] = []
        self._exclude_completed_root: Path | None = None
        self._exclude_ignore_keys: set[str] = set()
        self._should_shuffle = False

    def grid(self, param_grid: Mapping[str, Sequence[Any]]) -> "ExpManager":
        """按笛卡尔积扩展参数网格。

        Args:
            param_grid: 网格字典，例如
                ``{"lr": [1e-3, 1e-2], "batch_size": [16, 32]}``。

        Returns:
            ExpManager: 返回自身，支持链式调用。

        Notes:
            若 ``param_grid`` 为空，本方法为 no-op。
        """
        if not param_grid:
            return self

        keys = list(param_grid.keys())
        value_lists = [list(param_grid[key]) for key in keys]
        combos = list(itertools.product(*value_lists))

        expanded: list[ConfigDict] = []
        for base_config in self._configs:
            for combo in combos:
                next_config = copy.deepcopy(base_config)
                for key, value in zip(keys, combo):
                    next_config[key] = value
                expanded.append(next_config)

        self._configs = expanded
        return self

    def variants(
        self,
        variants: Sequence[Mapping[str, Any]] | Mapping[str, Sequence[Any]],
    ) -> "ExpManager":
        """按“独立变体”方式扩展配置。

        Args:
            variants: 推荐传 ``list[dict]``，例如
                ``[{"model": "tiny"}, {"model": "base", "layers": 12}]``。
                同时兼容旧格式 ``dict[str, list]``。

        Returns:
            ExpManager: 返回自身，支持链式调用。

        Notes:
            - ``list[dict]`` 语义更清晰，推荐优先使用。
            - ``dict[str, list]`` 会被转为单键变体集合。
        """
        if not variants:
            return self

        variant_dicts: list[ConfigDict] = []
        if isinstance(variants, Mapping):
            for key, values in variants.items():
                for value in values:
                    variant_dicts.append({key: value})
        else:
            variant_dicts = [dict(item) for item in variants]

        expanded: list[ConfigDict] = []
        for base_config in self._configs:
            for variant in variant_dicts:
                merged = copy.deepcopy(base_config)
                merged.update(copy.deepcopy(variant))
                expanded.append(merged)

        self._configs = expanded
        return self

    def modify(self, modifier: Modifier) -> "ExpManager":
        """注册配置修改器。

        Args:
            modifier: 修改函数。支持两种风格：
                1) 原地修改并返回 ``None``；
                2) 返回修改后的新字典。

        Returns:
            ExpManager: 返回自身。
        """
        self._modifiers.append(modifier)
        return self

    def where(self, predicate: Predicate) -> "ExpManager":
        """注册配置过滤器。

        Args:
            predicate: 谓词函数。返回 ``True`` 表示保留该配置。

        Returns:
            ExpManager: 返回自身。
        """
        self._predicates.append(predicate)
        return self

    def exclude_completed(
        self,
        results_root: str | Path,
        ignore_keys: Sequence[str] | None = None,
    ) -> "ExpManager":
        """排除已成功完成的配置。

        Args:
            results_root: 历史 run 根目录。
            ignore_keys: 配置对比时忽略的键（可选）。

        Returns:
            ExpManager: 返回自身。

        Notes:
            仅将满足以下条件的 run 视为“已完成”：
            1) ``run.json.schema_version == RUN_SCHEMA_VERSION``；
            2) ``run.json.status == succeeded``。
        """
        self._exclude_completed_root = Path(results_root)
        self._exclude_ignore_keys = set(ignore_keys or [])
        return self

    def shuffle(self) -> "ExpManager":
        """在最终构建结果上随机打乱顺序。

        Returns:
            ExpManager: 返回自身。
        """
        self._should_shuffle = True
        return self

    def build(self) -> list[ConfigDict]:
        """执行所有阶段并返回最终配置列表。

        Returns:
            list[dict[str, Any]]: 最终配置列表。

        Raises:
            TypeError: 当某个修改器返回值不是 ``dict`` 或 ``None``。

        Examples:
            >>> manager = ExpManager({"a": 1}).modify(lambda c: {**c, "b": 2})
            >>> manager.build()[0]["b"]
            2
        """
        configs = [copy.deepcopy(config) for config in self._configs]

        if self._modifiers:
            modified_configs: list[ConfigDict] = []
            for config in configs:
                next_config = config
                for modifier in self._modifiers:
                    result = modifier(next_config)
                    if result is None:
                        result = next_config
                    if not isinstance(result, dict):
                        raise TypeError("Modifier must return dict or None.")
                    next_config = result
                modified_configs.append(next_config)
            configs = modified_configs

        if self._predicates:
            filtered = []
            for config in configs:
                if all(predicate(config) for predicate in self._predicates):
                    filtered.append(config)
            configs = filtered

        if self._exclude_completed_root:
            completed_configs = self._load_completed_configs(self._exclude_completed_root)
            configs = [
                config
                for config in configs
                if not any(
                    self._configs_equal(config, completed, self._exclude_ignore_keys)
                    for completed in completed_configs
                )
            ]

        if self._should_shuffle:
            random.shuffle(configs)

        return configs

    # ---- v0.1 兼容别名 ----

    def add_grid_search(self, param_grid: Mapping[str, Sequence[Any]]) -> "ExpManager":
        """``grid`` 的兼容别名。"""
        return self.grid(param_grid)

    def add_variants(
        self,
        variant_space: Sequence[Mapping[str, Any]] | Mapping[str, Sequence[Any]],
    ) -> "ExpManager":
        """``variants`` 的兼容别名。"""
        return self.variants(variant_space)

    def add_modifier(self, modifier_func: Modifier) -> "ExpManager":
        """``modify`` 的兼容别名。"""
        return self.modify(modifier_func)

    def add_filter(self, filter_func: Predicate) -> "ExpManager":
        """``where`` 的兼容别名。"""
        return self.where(filter_func)

    def filter_completed(
        self,
        results_path: str | Path,
        ignore_keys: Sequence[str] | None = None,
    ) -> "ExpManager":
        """``exclude_completed`` 的兼容别名。"""
        return self.exclude_completed(results_path, ignore_keys=ignore_keys)

    def get_configs(self) -> list[ConfigDict]:
        """``build`` 的兼容别名。"""
        return self.build()

    # ---- 内部辅助函数 ----

    def _load_completed_configs(self, results_root: Path) -> list[ConfigDict]:
        """加载“已成功完成”实验的配置列表。

        Args:
            results_root: 历史 run 根目录。

        Returns:
            list[dict[str, Any]]: 已完成实验对应的配置字典列表。
        """
        if not results_root.exists():
            return []

        completed: list[ConfigDict] = []
        for run_dir in utils.get_subdirectories(results_root):
            run_meta = utils.load_json(run_dir / "run.json")
            if not run_meta:
                continue
            if run_meta.get("schema_version") != RUN_SCHEMA_VERSION:
                continue
            if run_meta.get("status") != RUN_STATUS_SUCCEEDED:
                continue

            config = utils.load_json(run_dir / "config.json")
            if isinstance(config, dict):
                completed.append(config)

        return completed

    def _configs_equal(self, a: ConfigDict, b: ConfigDict, ignore_keys: Iterable[str]) -> bool:
        """判断两个配置是否等价。

        Args:
            a: 配置 A。
            b: 配置 B。
            ignore_keys: 忽略键集合。

        Returns:
            bool: ``True`` 表示等价，``False`` 表示不等价。

        Notes:
            采用严格键集合比较，避免“缺字段却误判相等”的问题。
        """
        ignore = set(ignore_keys)
        left_keys = set(a.keys()) - ignore
        right_keys = set(b.keys()) - ignore
        if left_keys != right_keys:
            return False

        for key in left_keys:
            if self._normalize_value(a[key]) != self._normalize_value(b[key]):
                return False
        return True

    def _normalize_value(self, value: Any) -> Any:
        """归一化配置值，便于稳定比较。

        Args:
            value: 任意配置值。

        Returns:
            Any: 归一化后的值。

        Notes:
            - dict: 按 key 排序后递归归一化；
            - list/tuple: 统一为 list 并递归归一化。
        """
        if isinstance(value, dict):
            return {k: self._normalize_value(v) for k, v in sorted(value.items())}
        if isinstance(value, (list, tuple)):
            return [self._normalize_value(item) for item in value]
        return value
