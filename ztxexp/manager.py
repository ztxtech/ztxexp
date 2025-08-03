import argparse
import copy
import itertools
import random

from . import utils


class ExpManager:
    """
    Manages experiment configurations with support for grid search, variants,
    filtering, modification, and resuming from completed runs.
    """

    def __init__(self, base_args: argparse.Namespace):
        """Initializes with a base set of arguments."""
        self._base_configs = [copy.deepcopy(base_args)]
        self._configs = []
        self._modifiers = []
        self._filters = []
        self._is_generated = False

    def add_grid_search(self, param_grid: dict):
        """
        Expands configurations by a Cartesian product (grid search) of parameters.
        This should typically be the first method called after initialization.

        Args:
            param_grid (dict): e.g., {'lr': [0.1, 0.01], 'd_model': [32, 64]}
        """
        if not param_grid:
            return self

        keys = list(param_grid.keys())
        value_combinations = itertools.product(*(param_grid[key] for key in keys))

        new_configs = []
        for config in self._base_configs:
            # Create a fresh set of combinations for each base config
            # This is useful if you have multiple base configurations
            combinations_clone, value_combinations = itertools.tee(value_combinations)
            for combination in combinations_clone:
                new_config = copy.deepcopy(config)
                for key, value in zip(keys, combination):
                    setattr(new_config, key, value)
                new_configs.append(new_config)

        # Grid search results become the new base for further operations
        self._base_configs = new_configs
        return self

    def add_variants(self, variant_space: dict):
        """
        Adds new configurations as independent variations, not a grid search.
        For each key-value pair, it creates a new set of configs based on the current ones.

        Args:
            variant_space (dict): e.g., {'task': ['A', 'B'], 'seed': [100, 200]}
        """
        if not variant_space:
            return self

        # Start with the current base configurations
        variant_configs = list(self._base_configs)

        for key, values in variant_space.items():
            for value in values:
                # Create variants from the original base configs
                for base_config in self._base_configs:
                    new_config = copy.deepcopy(base_config)
                    setattr(new_config, key, value)
                    variant_configs.append(new_config)

        self._base_configs = variant_configs
        return self

    def add_modifier(self, modifier_func: callable):
        """
        Adds a function to modify each configuration.
        The function must accept a config (Namespace) and return a modified config.
        """
        self._modifiers.append(modifier_func)
        return self

    def add_filter(self, filter_func: callable):
        """
        Adds a function to filter configurations.
        The function must accept a config (Namespace) and return True to keep it.
        """
        self._filters.append(filter_func)
        return self

    def shuffle(self):
        """Randomly shuffles the generated configurations."""
        self._generate_if_needed()
        random.shuffle(self._configs)
        return self

    def filter_completed(self, results_path: str, ignore_keys: list[str] = None):
        """Filters out experiments that have already been completed."""
        self._generate_if_needed()
        if ignore_keys is None:
            ignore_keys = []  # Default keys to ignore

        completed_configs = self._load_completed_configs(results_path)
        if not completed_configs:
            print("No completed runs found to filter.")
            return self

        unrun_configs = []
        for config in self._configs:
            is_completed = any(
                self._are_configs_equal(vars(config), completed, ignore_keys)
                for completed in completed_configs
            )
            if not is_completed:
                unrun_configs.append(config)

        print(f"Generated {len(self._configs)} configs. "
              f"Found {len(completed_configs)} completed. "
              f"Remaining {len(unrun_configs)} to run.")
        self._configs = unrun_configs
        return self

    def get_configs(self) -> list[argparse.Namespace]:
        """
        Applies all modifiers and filters and returns the final configurations.
        This is the final step in the manager's pipeline.
        """
        self._generate_if_needed()
        return self._configs

    def _generate_if_needed(self):
        """Internal method to apply modifiers and filters once."""
        if self._is_generated:
            return

        current_configs = self._base_configs

        # Apply modifiers
        if self._modifiers:
            modified_configs = []
            for config in current_configs:
                temp_config = config
                for modifier in self._modifiers:
                    temp_config = modifier(temp_config)
                modified_configs.append(temp_config)
            current_configs = modified_configs

        # Apply filters
        if self._filters:
            filtered_configs = []
            for config in current_configs:
                if all(f(config) for f in self._filters):
                    filtered_configs.append(config)
            current_configs = filtered_configs

        self._configs = current_configs
        self._is_generated = True

    def _load_completed_configs(self, results_path: str) -> list[dict]:
        """Loads all 'args.json' from subfolders as completed experiments."""
        # ... (implementation from previous answer is unchanged) ...
        folders = utils.get_subdirectories(results_path)
        completed_configs = []
        for folder in folders:
            args_path = folder / 'args.json'
            if args_path.exists():
                args_dict = utils.load_json(str(args_path))
                if args_dict:
                    completed_configs.append(args_dict)
        return completed_configs

    def _are_configs_equal(self, config1: dict, config2: dict, ignore_keys: list[str]) -> bool:
        """Compares two configuration dictionaries."""
        # ... (implementation from previous answer is unchanged) ...
        keys1 = set(config1.keys()) - set(ignore_keys)
        keys2 = set(config2.keys()) - set(ignore_keys)

        # Allow comparison even if one config has extra keys (like metrics)
        common_keys = keys1.intersection(keys2)

        for key in common_keys:
            # Handle list vs tuple for JSON compatibility
            c1_val = tuple(config1[key]) if isinstance(config1[key], list) else config1[key]
            c2_val = tuple(config2[key]) if isinstance(config2[key], list) else config2[key]
            if c1_val != c2_val:
                return False
        return True
