# Overview (English)

`ztxexp` is an experiment framework for ML and LLM workflows.

## What it provides

1. Configuration building with chainable APIs.
2. Reproducible run artifacts in a strict v2 schema.
3. Built-in analyzers for aggregation, export, and cleanup.

## Core abstractions

- `ExpManager`: build configuration dictionaries.
- `ExpRunner`: execute configurations in sequential/parallel/dynamic mode.
- `ResultAnalyzer`: read and clean run artifacts.
- `ExperimentPipeline`: recommended facade for end-to-end workflows.

## Run artifact schema (v2)

Each run directory contains:

- `config.json`
- `run.json`
- `metrics.json` (optional)
- `artifacts/`

Success is defined by `run.json.status == "succeeded"`.

See [Quickstart](quickstart.en.md) for runnable examples.
