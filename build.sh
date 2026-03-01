#!/usr/bash

# Ensure stale artifacts from previous failed builds don't get uploaded.
rm -rf build dist *.egg-info

python -m build
twine check dist/*
twine upload dist/*
