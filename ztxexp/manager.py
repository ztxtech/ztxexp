"""Experiment configuration management for ztxexp v0.2."""

from __future__ import annotations

import argparse
import copy
import itertools
import random
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from ztxexp import utils
from ztxexp.constants import RUN_SCHEMA_VERSION, RUN_STATUS_SUCCEEDED

ConfigDict = dict[str, Any]
Modifier = Callable[[ConfigDict], ConfigDict | None]
Predicate = Callable[[ConfigDict], bool]


def _namespace_to_dict(value: argparse.Namespace | Mapping[str, Any]) -> ConfigDict:
    if isinstance(value, argparse.Namespace):
        return vars(value).copy()
    return dict(value)


class ExpManager:
    """Builds experiment configuration dictionaries using chainable operations."""

    def __init__(self, base_config: argparse.Namespace | Mapping[str, Any] | None = None):
        base = {} if base_config is None else _namespace_to_dict(base_config)
        self._configs: list[ConfigDict] = [base]
        self._modifiers: list[Modifier] = []
        self._predicates: list[Predicate] = []
        self._exclude_completed_root: Path | None = None
        self._exclude_ignore_keys: set[str] = set()
        self._should_shuffle = False

    def grid(self, param_grid: Mapping[str, Sequence[Any]]) -> "ExpManager":
        """Expands configs with a Cartesian product over the provided parameter grid."""
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
        """Adds independent variants on top of current configs.

        Preferred input is a list of dictionaries, for example:
            [{"model": "resnet"}, {"model": "transformer", "layers": 6}]

        A dict-of-lists is still accepted for convenience and translated into
        single-key variants.
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
        """Registers a modifier function. Modifier returns dict or mutates in-place."""
        self._modifiers.append(modifier)
        return self

    def where(self, predicate: Predicate) -> "ExpManager":
        """Registers a filter predicate. Only configs where predicate returns True survive."""
        self._predicates.append(predicate)
        return self

    def exclude_completed(
        self,
        results_root: str | Path,
        ignore_keys: Sequence[str] | None = None,
    ) -> "ExpManager":
        """Skips configs that already have a succeeded run in the v2 artifact format."""
        self._exclude_completed_root = Path(results_root)
        self._exclude_ignore_keys = set(ignore_keys or [])
        return self

    def shuffle(self) -> "ExpManager":
        """Shuffles final generated config order."""
        self._should_shuffle = True
        return self

    def build(self) -> list[ConfigDict]:
        """Builds final config dictionaries."""
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

    # Backward-compatible aliases
    def add_grid_search(self, param_grid: Mapping[str, Sequence[Any]]) -> "ExpManager":
        return self.grid(param_grid)

    def add_variants(
        self,
        variant_space: Sequence[Mapping[str, Any]] | Mapping[str, Sequence[Any]],
    ) -> "ExpManager":
        return self.variants(variant_space)

    def add_modifier(self, modifier_func: Modifier) -> "ExpManager":
        return self.modify(modifier_func)

    def add_filter(self, filter_func: Predicate) -> "ExpManager":
        return self.where(filter_func)

    def filter_completed(
        self,
        results_path: str | Path,
        ignore_keys: Sequence[str] | None = None,
    ) -> "ExpManager":
        return self.exclude_completed(results_path, ignore_keys=ignore_keys)

    def get_configs(self) -> list[ConfigDict]:
        return self.build()

    def _load_completed_configs(self, results_root: Path) -> list[ConfigDict]:
        if not results_root.exists():
            return []

        completed: list[ConfigDict] = []
        for run_dir in utils.get_subdirectories(str(results_root)):
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
        if isinstance(value, dict):
            return {k: self._normalize_value(v) for k, v in sorted(value.items())}
        if isinstance(value, (list, tuple)):
            return [self._normalize_value(item) for item in value]
        return value
