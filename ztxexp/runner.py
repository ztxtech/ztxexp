import argparse
import datetime
import logging
import time
import traceback
import uuid
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import psutil
# Joblib is a great library for parallelism, especially with numpy arrays.
# It can be a more robust choice than the standard ProcessPoolExecutor.
from joblib import Parallel, delayed

from . import utils

# Define a constant for the success marker file for consistency
SUCCESS_MARKER = '_SUCCESS'


class ExpRunner:
    """
    Runs a series of experiments based on a list of configurations,
    with support for multiple execution modes (sequential, parallel).
    """

    def __init__(self, configs: list[argparse.Namespace], exp_function, results_root: str):
        """
        Args:
            configs (list): A list of configuration Namespaces.
            exp_function (callable): The user-defined function for a single
                                     experiment. It must accept a single argument:
                                     (args: Namespace). The 'setting_path' will
                                     be added to the args object.
            results_root (str): The root directory to save results.
        """
        self.configs = configs
        self.exp_function = exp_function
        self.results_root = Path(results_root)
        utils.create_dir(str(self.results_root))

    def _run_single_experiment(self, args: argparse.Namespace):
        """
        A wrapper that executes a single experiment trial.
        It now adds 'setting_path' to the args object before calling exp_function.
        """
        uid = uuid.uuid4().hex[:6]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        setting_name = f"{timestamp}_{uid}"
        setting_path = self.results_root / setting_name

        # --- KEY CHANGE HERE ---
        # Add setting and path information directly to the args object
        args.setting = setting_name
        args.setting_path = setting_path

        thread_intro = f"--- Exp {args.setting} ---"
        print(thread_intro)

        try:
            # Step 1: Create directory and save the initial configuration
            utils.create_dir(str(args.setting_path))
            # We need to convert Path object to string for JSON serialization
            args_to_save = vars(args).copy()
            args_to_save['setting_path'] = str(args.setting_path)
            utils.save_json(args_to_save, args.setting_path / 'args.json')

            # Step 2: Execute the user's core experiment logic with the updated args
            self.exp_function(args)

            # Step 3: Create a success marker file upon completion
            (args.setting_path / SUCCESS_MARKER).touch()

            print(f"--- Exp {args.setting} Finished Successfully (marked with '{SUCCESS_MARKER}') ---")

        except Exception:
            error_msg = f"!!!!!! Experiment {args.setting} Failed !!!!!!"
            print(error_msg)
            traceback.print_exc()
            with open(args.setting_path / 'error.log', 'w') as f:
                f.write(error_msg + "\n" + traceback.format_exc())

    def run(self,
            execution_mode: str = 'sequential',
            num_workers: int = 4,
            dynamic_cpu_threshold: int = 80):
        """
        Executes all experiments using the specified mode.

        Args:
            execution_mode (str): The mode of execution. Options:
                - 'sequential': Runs experiments one by one in the main process.
                - 'process_pool': Uses the standard library's ProcessPoolExecutor.
                - 'joblib': Uses the joblib library for robust parallel processing.
                - 'dynamic': (Conceptual) A custom mode to adjust workers based on CPU load.
            num_workers (int): The number of parallel worker processes.
            dynamic_cpu_threshold (int): The CPU usage threshold for the 'dynamic' mode.
        """
        total_exps = len(self.configs)
        if not total_exps:
            print("No experiment configurations to run.")
            return

        print(f"\nStarting experiment run with {total_exps} configurations.")
        print(f"Execution Mode: {execution_mode}, Workers: {num_workers if execution_mode != 'sequential' else 1}\n")

        if execution_mode == 'sequential':
            for args in self.configs:
                self._run_single_experiment(args)

        elif execution_mode == 'process_pool':
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                # The map function is simple and effective.
                list(executor.map(self._run_single_experiment, self.configs))

        elif execution_mode == 'joblib':
            # Joblib is often preferred for scientific computing.
            Parallel(n_jobs=num_workers, prefer='processes')(
                delayed(self._run_single_experiment)(args) for args in self.configs)

        elif execution_mode == 'dynamic':
            # This is a placeholder for your custom dynamic logic.
            # It ensures that new tasks are only submitted if CPU usage is below a threshold.
            print("Running in dynamic mode. NOTE: This is a conceptual implementation.")
            logging.basicConfig(level=logging.INFO, filename='./my_results/dynamic.log', filemode='w')
            self._dynamic_parallel_run(max_workers=num_workers, cpu_threshold=dynamic_cpu_threshold)

        else:
            raise ValueError(f"Invalid execution_mode: '{execution_mode}'. "
                             "Choose from 'sequential', 'process_pool', 'joblib', 'dynamic'.")

        print("\nAll experiment runs have been processed.")

    def _dynamic_parallel_run(self, max_workers: int, cpu_threshold: int):
        """
        A conceptual implementation of a dynamic parallel runner.
        It submits jobs to a process pool but pauses if CPU usage is too high.
        """

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._run_single_experiment, args): args for args in self.configs}

            while futures:
                # Check CPU usage before waiting for the next task
                cpu_percent = psutil.cpu_percent(interval=1)
                logging.info(
                    f"Current CPU usage: {cpu_percent}%. Active workers: {executor._max_workers - executor._idle_worker_semaphore._value}")

                if cpu_percent < cpu_threshold:
                    # Wait for at least one task to complete
                    done, _ = as_completed(futures, timeout=60)
                    if not done:
                        logging.warning("No task completed in 60 seconds.")
                        continue

                    for future in done:
                        # Remove the completed future
                        futures.pop(future)
                        logging.info(f"Task for args {future.result()} completed.")
                else:
                    logging.warning(
                        f"CPU usage {cpu_percent}% is above threshold {cpu_threshold}%. Pausing job submission.")
                    time.sleep(10)  # Wait before checking again
