# Welcome to `ztxexp`

[![GitHub Stars](https://img.shields.io/github/stars/ztxtech/ztxexp?style=social)](https://github.com/ztxtech/ztxexp/)
[![PyPI version](https://badge.fury.io/py/ztxexp.svg)](https://badge.fury.io/py/ztxexp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Versions](https://img.shields.io/pypi/pyversions/ztxexp.svg)](https://pypi.org/project/ztxexp)


> A lightweight, powerful, and developer-friendly Python library designed to streamline and automate the management, execution, and analysis of computational experiments.

-----

### What is ztxexp?

In machine learning, data science, or any computationally intensive research, we often need to run hundreds or thousands of experiments. These experiments typically involve complex parameter combinations, long runtimes, and a huge number of result files. Managing all of this manually quickly becomes a nightmare.

**ztxexp** was created to solve this exact pain point. It provides an elegant and fluent API that abstracts the entire experimental workflow into three core stages, allowing you to focus on the experiment itself, rather than tedious administrative tasks.

### Core Workflow: Manage -\> Run -\> Analyze

The key to understanding `ztxexp` is its core three-stage workflow:

1.  **Manage**

      * Use `ztxexp.ExpManager` to define your parameter space. Whether it's a simple grid search or complex multi-conditional variants, everything can be easily constructed through a fluent, chainable API. You can also inject custom modification and filtering logic to handle tricky parameter dependencies.

2.  **Run**

      * Hand the generated list of configurations over to `ztxexp.ExpRunner`. It intelligently skips experiments that have already completed successfully and utilizes multi-core CPUs for parallel processing, significantly shortening the experiment cycle. All run statuses and logs are properly recorded.

3.  **Analyze**

      * After the experiments are finished, `ztxexp.ResultAnalyzer` can, with a single command, aggregate the results from all successful runs, generating a clean `Pandas DataFrame`, a summary CSV file, and a ranked pivot table. It also helps you safely clean up result files from failed or no-longer-needed experiments.

### Quick Start

Ready to boost your experiment efficiency? Start here:

| Link | Description |
| :--- | :--- |
| **🚀 Installation & Configuration** | Learn how to quickly install `ztxexp` and configure your first project. |
| **🧑‍💻 Quick Start Tutorial** | Follow a complete end-to-end example to experience the core workflow of ztxexp. |
| **📚 Full API Reference** | Dive deep into the detailed usage and parameter descriptions for every class and function. |
| **💡 More Examples** | Browse multiple example scripts that include advanced usage and tips. |