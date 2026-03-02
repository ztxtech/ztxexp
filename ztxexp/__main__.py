"""Module entrypoint for ``python -m ztxexp``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
