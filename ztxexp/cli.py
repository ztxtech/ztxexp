"""ztxexp command line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ztxexp.skill import (
    SUPPORTED_SKILL_LANGUAGES,
    SUPPORTED_SKILL_TARGETS,
    choose_target_mode_interactive,
    init_skill,
    is_interactive_terminal,
    remove_skill,
    render_openai_yaml,
    show_skill,
)
from ztxexp.vibe import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_PROFILES,
    init_vibe,
    remove_vibe,
    show_vibe,
)


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

    skill_common = argparse.ArgumentParser(add_help=False)
    skill_common.add_argument(
        "--project-root",
        type=str,
        default=None,
        help="Target project root directory. Default: current working directory.",
    )
    skill_common.add_argument(
        "--target",
        choices=SUPPORTED_SKILL_TARGETS,
        default=None,
        help="Skill install target: skills/codex/both.",
    )
    skill_common.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes only and do not write files.",
    )
    skill_common.add_argument(
        "--force",
        action="store_true",
        help="Allow overwrite/remove unmanaged target directories.",
    )

    init_skill_parser = subparsers.add_parser(
        "init-skill",
        parents=[skill_common],
        help="Install or update built-in ztx-exp-manager skill in target project.",
    )
    init_skill_parser.add_argument(
        "--language",
        choices=SUPPORTED_SKILL_LANGUAGES,
        default="bilingual",
        help="Skill markdown language. Default: bilingual.",
    )
    init_skill_parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Disable interactive target selection and fall back to default target.",
    )

    show_skill_parser = subparsers.add_parser(
        "show-skill",
        help="Show built-in ztx-exp-manager skill content.",
    )
    show_skill_parser.add_argument(
        "--language",
        choices=SUPPORTED_SKILL_LANGUAGES,
        default="bilingual",
        help="Skill markdown language. Default: bilingual.",
    )
    show_skill_parser.add_argument(
        "--with-openai",
        action="store_true",
        help="Also print agents/openai.yaml preview.",
    )

    subparsers.add_parser(
        "remove-skill",
        parents=[skill_common],
        help="Remove installed ztx-exp-manager skill from target project.",
    )

    return parser


def _print_result_summary(command: str, target: Path, action: str, changed: bool) -> None:
    print(f"[{command}] target={target}")
    print(f"[{command}] action={action}, changed={changed}")


def _print_skill_results(command: str, result) -> None:
    print(
        f"[{command}] project_root={result.project_root}, "
        f"target_mode={result.target_mode}, dry_run={result.dry_run}"
    )
    for line in result.summary_lines():
        print(f"[{command}] {line}")


def _handle_init_vibe(args: argparse.Namespace) -> int:
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


def _handle_show_vibe(args: argparse.Namespace) -> int:
    print(show_vibe(profile=args.profile, language=args.language))
    return 0


def _handle_remove_vibe(args: argparse.Namespace) -> int:
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


def _resolve_init_skill_target(args: argparse.Namespace) -> str:
    if args.target:
        return args.target
    if args.no_interactive or not is_interactive_terminal():
        print("[init-skill] interactive prompt disabled, defaulting target to 'skills'.")
        return "skills"
    return choose_target_mode_interactive()


def _handle_init_skill(args: argparse.Namespace) -> int:
    target_mode = _resolve_init_skill_target(args)
    result = init_skill(
        project_root=args.project_root,
        target_mode=target_mode,
        language=args.language,
        dry_run=args.dry_run,
        force=args.force,
    )
    _print_skill_results("init-skill", result)
    return 0


def _handle_show_skill(args: argparse.Namespace) -> int:
    print(show_skill(language=args.language).rstrip())
    if args.with_openai:
        print("\n# agents/openai.yaml\n")
        print(render_openai_yaml().rstrip())
    return 0


def _handle_remove_skill(args: argparse.Namespace) -> int:
    target_mode = args.target or "both"
    result = remove_skill(
        project_root=args.project_root,
        target_mode=target_mode,
        dry_run=args.dry_run,
        force=args.force,
    )
    _print_skill_results("remove-skill", result)
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI main entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "init-vibe":
            return _handle_init_vibe(args)
        if args.command == "show-vibe":
            return _handle_show_vibe(args)
        if args.command == "remove-vibe":
            return _handle_remove_vibe(args)
        if args.command == "init-skill":
            return _handle_init_skill(args)
        if args.command == "show-skill":
            return _handle_show_skill(args)
        if args.command == "remove-skill":
            return _handle_remove_skill(args)
        parser.error(f"Unknown command: {args.command}")
        return 2
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
