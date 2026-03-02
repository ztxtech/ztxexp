"""ztxexp command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ztxexp.vibe import SUPPORTED_LANGUAGES, SUPPORTED_PROFILES, init_vibe, remove_vibe, show_vibe


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(prog="ztxexp", description="ztxexp command line tools")
    subparsers = parser.add_subparsers(dest="command", required=True)

    common_rw = argparse.ArgumentParser(add_help=False)
    common_rw.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Target project root directory. Default: current working directory.",
    )
    common_rw.add_argument(
        "--agents-file",
        type=str,
        default=None,
        help="Explicit AGENTS file path. Relative paths are resolved from project root.",
    )
    common_rw.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes only and do not write files.",
    )

    init_parser = subparsers.add_parser(
        "init-vibe",
        parents=[common_rw],
        help="Initialize or update ztxexp managed agent block.",
    )
    init_parser.add_argument(
        "--profile",
        choices=SUPPORTED_PROFILES,
        default="webcoding",
        help="Agent profile. Default: webcoding.",
    )
    init_parser.add_argument(
        "--language",
        choices=SUPPORTED_LANGUAGES,
        default="bilingual",
        help="Rendered block language. Default: bilingual.",
    )

    show_parser = subparsers.add_parser(
        "show-vibe",
        help="Show the managed agent block content.",
    )
    show_parser.add_argument(
        "--profile",
        choices=SUPPORTED_PROFILES,
        default="webcoding",
        help="Agent profile. Default: webcoding.",
    )
    show_parser.add_argument(
        "--language",
        choices=SUPPORTED_LANGUAGES,
        default="bilingual",
        help="Rendered block language. Default: bilingual.",
    )

    subparsers.add_parser(
        "remove-vibe",
        parents=[common_rw],
        help="Remove ztxexp managed agent block from AGENTS file.",
    )

    return parser


def _print_result_summary(command: str, target: Path, action: str, changed: bool) -> None:
    print(f"[{command}] target={target}")
    print(f"[{command}] action={action}, changed={changed}")


def _handle_init(args: argparse.Namespace) -> int:
    result = init_vibe(
        project_root=args.project_root,
        agents_file=args.agents_file,
        profile=args.profile,
        language=args.language,
        dry_run=args.dry_run,
    )
    _print_result_summary("init-vibe", result.target_file, result.action, result.changed)
    print(f"[init-vibe] profile={args.profile}, language={args.language}, dry_run={args.dry_run}")
    if args.dry_run:
        diff = result.diff_text()
        print(diff if diff else "[init-vibe] no changes")
    return 0


def _handle_show(args: argparse.Namespace) -> int:
    print(show_vibe(profile=args.profile, language=args.language))
    return 0


def _handle_remove(args: argparse.Namespace) -> int:
    result = remove_vibe(
        project_root=args.project_root,
        agents_file=args.agents_file,
        dry_run=args.dry_run,
    )
    _print_result_summary("remove-vibe", result.target_file, result.action, result.changed)
    if args.dry_run:
        diff = result.diff_text()
        print(diff if diff else "[remove-vibe] no changes")
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI main entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init-vibe":
            return _handle_init(args)
        if args.command == "show-vibe":
            return _handle_show(args)
        if args.command == "remove-vibe":
            return _handle_remove(args)
        parser.error(f"Unknown command: {args.command}")
        return 2
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
