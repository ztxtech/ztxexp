#!/usr/bin/env sh
set -eu

cmd="${1:-build}"

case "$cmd" in
  build)
    NO_MKDOCS_2_WARNING=1 mkdocs build --strict
    ;;
  serve)
    NO_MKDOCS_2_WARNING=1 mkdocs serve
    ;;
  clean)
    rm -rf docs
    ;;
  *)
    echo "Usage: sh mk.sh [build|serve|clean]" >&2
    exit 1
    ;;
esac
