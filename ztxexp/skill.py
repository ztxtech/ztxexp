"""Skill integration helpers for ztxexp CLI.

This module manages first-party skill installation/removal workflows.
The default built-in skill is ``ztx-exp-manager``.
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ztxexp import __version__, utils

SKILL_NAME = "ztx-exp-manager"
SKILL_MARKER_FILENAME = ".ztxexp-managed-skill.json"

SUPPORTED_SKILL_LANGUAGES = ("bilingual", "zh", "en")
SUPPORTED_SKILL_TARGETS = ("skills", "codex", "both")

SkillLanguage = Literal["bilingual", "zh", "en"]
SkillTargetMode = Literal["skills", "codex", "both"]


@dataclass(slots=True)
class SkillTargetResult:
    """Single target operation result."""

    target_dir: Path
    action: str
    changed: bool
    message: str = ""


@dataclass(slots=True)
class SkillOperationResult:
    """Aggregated multi-target skill operation result."""

    project_root: Path
    target_mode: SkillTargetMode
    dry_run: bool
    results: list[SkillTargetResult] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        """Return whether any target changed."""
        return any(item.changed for item in self.results)

    def summary_lines(self) -> list[str]:
        """Build human-readable summary lines."""
        lines = []
        for item in self.results:
            suffix = f", note={item.message}" if item.message else ""
            lines.append(
                f"target={item.target_dir}, action={item.action}, changed={item.changed}{suffix}"
            )
        return lines


def resolve_project_root(project_root: str | Path | None) -> Path:
    """Resolve project root path and validate existence."""
    root = Path.cwd() if project_root is None else Path(project_root)
    root = root.expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")
    if not root.exists():
        raise ValueError(f"project root does not exist: {root}")
    return root


def resolve_skill_targets(project_root: Path, target_mode: SkillTargetMode) -> list[Path]:
    """Resolve concrete skill target directories from target mode."""
    if target_mode not in SUPPORTED_SKILL_TARGETS:
        raise ValueError(f"unsupported target mode: {target_mode}")

    skills_target = project_root / "skills" / SKILL_NAME
    codex_target = project_root / ".codex" / "skills" / SKILL_NAME

    if target_mode == "skills":
        return [skills_target]
    if target_mode == "codex":
        return [codex_target]
    return [skills_target, codex_target]


def choose_target_mode_interactive(max_attempts: int = 3) -> SkillTargetMode:
    """Prompt user to choose skill install target mode.

    Args:
        max_attempts: Maximum invalid retries.

    Returns:
        SkillTargetMode: Selected mode.

    Raises:
        ValueError: If input remains invalid after max retries.
    """
    print("请选择 skill 安装位置：")
    print("  1) 只写入 skills/")
    print("  2) 只写入 .codex/skills/")
    print("  3) 同时写入两处")

    choices = {"1": "skills", "2": "codex", "3": "both"}
    for _ in range(max_attempts):
        raw = input("请输入选项 [1/2/3]: ").strip()
        if raw in choices:
            return choices[raw]  # type: ignore[return-value]
        print("输入无效，请输入 1、2 或 3。")

    raise ValueError("Invalid selection after 3 attempts.")


def render_skill_markdown(language: SkillLanguage = "bilingual") -> str:
    """Render built-in ``ztx-exp-manager`` skill markdown content."""
    if language not in SUPPORTED_SKILL_LANGUAGES:
        raise ValueError(f"unsupported language: {language}")

    frontmatter = (
        "---\n"
        "name: ztx-exp-manager\n"
        "description: Manage ML/LLM experiment workflows with ztxexp. "
        "Use when the agent needs to build parameter configurations, run experiments, "
        "validate run artifacts, analyze results, or troubleshoot failed runs.\n"
        "---\n\n"
    )

    zh_body = """# ztx-exp-manager Skill（中文）

## 核心规则

1. 优先使用 `ExperimentPipeline` 组织实验，不手写零散调度脚本。
2. 实验函数契约固定为：`exp_fn(ctx: RunContext) -> dict | None`。
3. 成功判定必须使用：`run.json.status == "succeeded"`。
4. 产物分工：
   - 最终指标：`return dict` -> `metrics.json`
   - 过程指标：`ctx.log_metric(...)` -> `metrics.jsonl`
   - 业务文件：写入 `artifacts/`

## 常用流程

1. 先用 `grid/variants/random_search` 构建配置。
2. 再执行 `pipeline.run(exp_fn, mode=...)`。
3. 用 `ResultAnalyzer` 聚合、导出和清理。

## 常用命令

- `pip install -U ztxexp`
- `ztxexp init-vibe`
- `python -m pytest`

## 排障清单

1. 先看 `run.json.status`。
2. 失败时查看 `error.log`。
3. 曲线缺失时检查 `ctx.log_metric(...)` 是否调用。
"""

    en_body = """# ztx-exp-manager Skill (English)

## Core Rules

1. Prefer `ExperimentPipeline` for workflow orchestration.
2. Keep experiment contract: `exp_fn(ctx: RunContext) -> dict | None`.
3. Determine success strictly by `run.json.status == "succeeded"`.
4. Artifact responsibilities:
   - Final metrics: `return dict` -> `metrics.json`
   - Step metrics: `ctx.log_metric(...)` -> `metrics.jsonl`
   - Business outputs: write into `artifacts/`

## Typical Workflow

1. Build configs via `grid/variants/random_search`.
2. Execute with `pipeline.run(exp_fn, mode=...)`.
3. Aggregate and clean results using `ResultAnalyzer`.

## Common Commands

- `pip install -U ztxexp`
- `ztxexp init-vibe`
- `python -m pytest`

## Troubleshooting

1. Check `run.json.status` first.
2. Read `error.log` on failure.
3. Verify `ctx.log_metric(...)` for missing curves.
"""

    if language == "zh":
        body = zh_body.strip()
    elif language == "en":
        body = en_body.strip()
    else:
        body = f"{zh_body.strip()}\n\n---\n\n{en_body.strip()}"

    return frontmatter + body + "\n"


def render_openai_yaml() -> str:
    """Render first-party `agents/openai.yaml` metadata."""
    return (
        "display_name: ztx-exp-manager\n"
        "short_description: Build and govern ML/LLM experiment workflows with ztxexp.\n"
        "default_prompt: >-\n"
        "  Use ExperimentPipeline and RunContext to build reproducible experiments,\n"
        "  enforce run artifact protocol, and analyze failures by run status and logs.\n"
    )


def show_skill(language: SkillLanguage = "bilingual") -> str:
    """Preview built-in skill markdown content."""
    return render_skill_markdown(language=language)


def is_interactive_terminal() -> bool:
    """Return whether both stdin and stdout are interactive terminals."""
    return bool(sys.stdin.isatty() and sys.stdout.isatty())


def _marker_path(target_dir: Path) -> Path:
    return target_dir / SKILL_MARKER_FILENAME


def _load_json(path: Path) -> dict[str, object] | None:
    try:
        data = utils.load_json(path)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _is_managed_target(target_dir: Path) -> bool:
    marker = _load_json(_marker_path(target_dir))
    if marker is None:
        return False
    return (
        marker.get("skill_name") == SKILL_NAME
        and marker.get("installed_by") == "ztxexp init-skill"
    )


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _dump_marker(language: SkillLanguage, installed_at: str) -> str:
    payload = {
        "skill_name": SKILL_NAME,
        "installed_by": "ztxexp init-skill",
        "version": __version__,
        "language": language,
        "installed_at": installed_at,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def init_skill(
    project_root: str | Path | None = None,
    target_mode: SkillTargetMode = "skills",
    language: SkillLanguage = "bilingual",
    dry_run: bool = False,
    force: bool = False,
) -> SkillOperationResult:
    """Install/update built-in skill into one or more target directories."""
    root = resolve_project_root(project_root)
    targets = resolve_skill_targets(root, target_mode)

    expected_skill_md = render_skill_markdown(language=language)
    expected_openai_yaml = render_openai_yaml()

    op = SkillOperationResult(
        project_root=root,
        target_mode=target_mode,
        dry_run=dry_run,
        results=[],
    )

    for target in targets:
        marker_path = _marker_path(target)
        existed = target.exists()
        managed = _is_managed_target(target) if existed else False

        if existed and not managed and not force:
            op.results.append(
                SkillTargetResult(
                    target_dir=target,
                    action="skipped_unmanaged",
                    changed=False,
                    message="target exists without ztxexp managed marker",
                )
            )
            continue

        old_skill_md = _read_text(target / "SKILL.md")
        old_openai_yaml = _read_text(target / "agents" / "openai.yaml")
        old_marker = _load_json(marker_path) or {}

        old_marker_base = {
            "skill_name": old_marker.get("skill_name"),
            "installed_by": old_marker.get("installed_by"),
            "version": old_marker.get("version"),
            "language": old_marker.get("language"),
        }
        expected_marker_base = {
            "skill_name": SKILL_NAME,
            "installed_by": "ztxexp init-skill",
            "version": __version__,
            "language": language,
        }

        files_changed = (
            old_skill_md != expected_skill_md
            or old_openai_yaml != expected_openai_yaml
            or old_marker_base != expected_marker_base
        )
        changed = (not existed) or files_changed

        if not changed:
            op.results.append(
                SkillTargetResult(
                    target_dir=target,
                    action="unchanged",
                    changed=False,
                )
            )
            continue

        installed_at = utils.utc_now_iso()
        marker_text = _dump_marker(language=language, installed_at=installed_at)
        action = "create" if not existed else "update"

        if not dry_run:
            (target / "agents").mkdir(parents=True, exist_ok=True)
            (target / "SKILL.md").write_text(expected_skill_md, encoding="utf-8")
            (target / "agents" / "openai.yaml").write_text(
                expected_openai_yaml,
                encoding="utf-8",
            )
            marker_path.write_text(marker_text, encoding="utf-8")

        if dry_run:
            action = f"would_{action}"

        op.results.append(
            SkillTargetResult(
                target_dir=target,
                action=action,
                changed=True,
            )
        )

    return op


def remove_skill(
    project_root: str | Path | None = None,
    target_mode: SkillTargetMode = "both",
    dry_run: bool = False,
    force: bool = False,
) -> SkillOperationResult:
    """Remove installed built-in skill from one or more target directories."""
    root = resolve_project_root(project_root)
    targets = resolve_skill_targets(root, target_mode)

    op = SkillOperationResult(
        project_root=root,
        target_mode=target_mode,
        dry_run=dry_run,
        results=[],
    )

    for target in targets:
        if not target.exists():
            op.results.append(
                SkillTargetResult(
                    target_dir=target,
                    action="not_found",
                    changed=False,
                )
            )
            continue

        managed = _is_managed_target(target)
        if not managed and not force:
            op.results.append(
                SkillTargetResult(
                    target_dir=target,
                    action="skipped_unmanaged",
                    changed=False,
                    message="target exists without ztxexp managed marker",
                )
            )
            continue

        action = "removed"
        if dry_run:
            action = "would_remove"
        else:
            shutil.rmtree(target)

        op.results.append(
            SkillTargetResult(
                target_dir=target,
                action=action,
                changed=True,
            )
        )

    return op
