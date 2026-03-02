#!/usr/bin/env bash
set -euo pipefail

rm -rf build dist *.egg-info

python -m build --no-isolation
python -m twine check dist/*
python -m twine upload dist/*
