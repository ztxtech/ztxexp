"""Agent integration helpers for ztxexp CLI.

This module provides reusable functions used by ``ztxexp init-vibe`` style
commands. It is intentionally independent from argument parsing so it can be
tested directly.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

START_MARKER = "<!-- ztxexp:vibe:start -->"
END_MARKER = "<!-- ztxexp:vibe:end -->"

SUPPORTED_PROFILES = ("webcoding", "codex", "cursor", "cline", "copilot")
SUPPORTED_LANGUAGES = ("bilingual", "zh", "en")
DEFAULT_AGENTS_FILES = ("AGENTS.md", "agents.md", "agents.MD")

ProfileType = Literal["webcoding", "codex", "cursor", "cline", "copilot"]
LanguageType = Literal["bilingual", "zh", "en"]

_BLOCK_PATTERN = re.compile(
    rf"{re.escape(START_MARKER)}.*?{re.escape(END_MARKER)}\n?",
    flags=re.DOTALL,
)

_PROFILE_HINTS = {
    "webcoding": {
        "zh": "适用于通用 Web Coding Agent（Codex/Cursor/Cline/Copilot）。",
        "en": "Applies to general Web coding agents (Codex/Cursor/Cline/Copilot).",
    },
    "codex": {
        "zh": "针对 Codex 工作流优化。",
        "en": "Optimized for Codex workflows.",
    },
    "cursor": {
        "zh": "针对 Cursor Agent 工作流优化。",
        "en": "Optimized for Cursor Agent workflows.",
    },
    "cline": {
        "zh": "针对 Cline 工作流优化。",
        "en": "Optimized for Cline workflows.",
    },
    "copilot": {
        "zh": "针对 GitHub Copilot Agent 工作流优化。",
        "en": "Optimized for GitHub Copilot Agent workflows.",
    },
}


@dataclass(slots=True)
class VibeOperationResult:
    """Result of a managed block operation."""

    target_file: Path
    action: str
    changed: bool
    old_content: str
    new_content: str

    def diff_text(self) -> str:
        """Build a unified diff for preview output."""
        before = self.old_content.splitlines(keepends=True)
        after = self.new_content.splitlines(keepends=True)
        if before == after:
            return ""
        diff = difflib.unified_diff(
            before,
            after,
            fromfile=f"{self.target_file} (before)",
            tofile=f"{self.target_file} (after)",
        )
        return "".join(diff)


def resolve_project_root(project_root: str | Path | None) -> Path:
    """Resolve and validate project root directory."""
    root = Path.cwd() if project_root is None else Path(project_root)
    root = root.expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")
    if not root.exists():
        raise ValueError(f"project root does not exist: {root}")
    return root


def resolve_agents_file(project_root: Path, agents_file: str | Path | None = None) -> Path:
    """Resolve target agents file according to matching policy."""
    if agents_file is not None:
        explicit_path = Path(agents_file).expanduser()
        if not explicit_path.is_absolute():
            explicit_path = project_root / explicit_path
        return explicit_path.resolve()

    for filename in DEFAULT_AGENTS_FILES:
        candidate = project_root / filename
        if candidate.exists():
            return candidate.resolve()
    return (project_root / DEFAULT_AGENTS_FILES[0]).resolve()


def render_vibe_block(
    profile: ProfileType = "webcoding",
    language: LanguageType = "bilingual",
) -> str:
    """Render managed block content by profile and language."""
    if profile not in SUPPORTED_PROFILES:
        raise ValueError(f"unsupported profile: {profile}")
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported language: {language}")

    hints = _PROFILE_HINTS[profile]

    zh_section = f"""## ztxexp Agent 使用约定（受管区块）

- Profile: `{profile}`
- 说明：{hints["zh"]}
- 本项目已启用 `ztxexp`，请优先基于以下抽象完成实验代码：
  - `ExperimentPipeline`
  - `RunContext`
  - `ResultAnalyzer`
- 实验函数契约：`exp_fn(ctx: RunContext) -> dict | None`
- 成功判定：`run.json.status == "succeeded"`
- 常用命令：
  - `pip install -U ztxexp`
  - `python -m pytest`
  - `python -m ztxexp show-vibe`

最小代码示例：

```python
from ztxexp import ExperimentPipeline, RunContext

def exp_fn(ctx: RunContext):
    return {{"score": 1.0}}

summary = (
    ExperimentPipeline("./results")
    .grid({{"seed": [42]}})
    .run(exp_fn, mode="sequential")
)
print(summary)
```
"""

    en_section = f"""## ztxexp Agent Guidelines (Managed Block)

- Profile: `{profile}`
- Note: {hints["en"]}
- This project uses `ztxexp`. Prefer these abstractions in generated code:
  - `ExperimentPipeline`
  - `RunContext`
  - `ResultAnalyzer`
- Experiment contract: `exp_fn(ctx: RunContext) -> dict | None`
- Success criteria: `run.json.status == "succeeded"`
- Common commands:
  - `pip install -U ztxexp`
  - `python -m pytest`
  - `python -m ztxexp show-vibe`

Minimal example:

```python
from ztxexp import ExperimentPipeline, RunContext

def exp_fn(ctx: RunContext):
    return {{"score": 1.0}}

summary = (
    ExperimentPipeline("./results")
    .grid({{"seed": [42]}})
    .run(exp_fn, mode="sequential")
)
print(summary)
```
"""

    if language == "zh":
        payload = zh_section.strip()
    elif language == "en":
        payload = en_section.strip()
    else:
        payload = f"{zh_section.strip()}\n\n---\n\n{en_section.strip()}"

    return f"{START_MARKER}\n{payload}\n{END_MARKER}\n"


def _upsert_managed_block(
    existing_content: str,
    block_content: str,
    file_exists: bool,
) -> tuple[str, str]:
    """Insert or replace managed block and return updated text + action."""
    match = _BLOCK_PATTERN.search(existing_content)
    if match:
        next_content = (
            existing_content[: match.start()] + block_content + existing_content[match.end() :]
        )
        action = "update"
    else:
        prefix = existing_content.rstrip("\n")
        if prefix:
            next_content = f"{prefix}\n\n{block_content}"
            action = "update"
        else:
            next_content = block_content
            action = "create" if not file_exists else "update"
    return next_content, action


def _remove_managed_block(existing_content: str) -> tuple[str, bool]:
    """Remove managed block if exists."""
    updated, removed_count = _BLOCK_PATTERN.subn("", existing_content, count=1)
    if removed_count == 0:
        return existing_content, False
    updated = re.sub(r"\n{3,}", "\n\n", updated).strip() + "\n"
    if updated == "\n":
        updated = ""
    return updated, True


def init_vibe(
    project_root: str | Path | None = None,
    agents_file: str | Path | None = None,
    profile: ProfileType = "webcoding",
    language: LanguageType = "bilingual",
    dry_run: bool = False,
) -> VibeOperationResult:
    """Create or update managed vibe block in target project."""
    root = resolve_project_root(project_root)
    target = resolve_agents_file(root, agents_file)
    file_exists = target.exists()
    old_content = target.read_text(encoding="utf-8") if file_exists else ""
    block = render_vibe_block(profile=profile, language=language)
    new_content, action = _upsert_managed_block(old_content, block, file_exists=file_exists)
    changed = old_content != new_content

    if changed and not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(new_content, encoding="utf-8")
    if not changed:
        action = "unchanged"

    return VibeOperationResult(
        target_file=target,
        action=action,
        changed=changed,
        old_content=old_content,
        new_content=new_content,
    )


def remove_vibe(
    project_root: str | Path | None = None,
    agents_file: str | Path | None = None,
    dry_run: bool = False,
) -> VibeOperationResult:
    """Remove managed vibe block from target project."""
    root = resolve_project_root(project_root)
    target = resolve_agents_file(root, agents_file)
    if not target.exists():
        return VibeOperationResult(
            target_file=target,
            action="not_found",
            changed=False,
            old_content="",
            new_content="",
        )

    old_content = target.read_text(encoding="utf-8")
    new_content, removed = _remove_managed_block(old_content)
    changed = removed and new_content != old_content

    if changed and not dry_run:
        target.write_text(new_content, encoding="utf-8")

    action = "removed" if removed else "no_block"
    return VibeOperationResult(
        target_file=target,
        action=action,
        changed=changed,
        old_content=old_content,
        new_content=new_content,
    )


def show_vibe(profile: ProfileType = "webcoding", language: LanguageType = "bilingual") -> str:
    """Preview managed block content."""
    return render_vibe_block(profile=profile, language=language)
