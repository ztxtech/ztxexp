from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import tomllib

import ztxexp
from ztxexp.cli import build_parser
from ztxexp.vibe import END_MARKER, START_MARKER, init_vibe, remove_vibe, show_vibe


def test_cli_help_and_subcommands():
    parser = build_parser()
    help_text = parser.format_help()
    assert "init-vibe" in help_text
    assert "show-vibe" in help_text
    assert "remove-vibe" in help_text


def test_init_vibe_create_default_agents_file(tmp_path):
    result = init_vibe(project_root=tmp_path)
    target = tmp_path / "AGENTS.md"
    assert result.target_file == target.resolve()
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert START_MARKER in content
    assert END_MARKER in content
    assert "ExperimentPipeline" in content


def test_init_vibe_reuse_existing_agents_filename(tmp_path):
    target = tmp_path / "agents.md"
    target.write_text("custom\n", encoding="utf-8")

    result = init_vibe(project_root=tmp_path)
    assert result.target_file == target.resolve()
    assert START_MARKER in target.read_text(encoding="utf-8")


def test_init_vibe_prefers_uppercase_agents_file(tmp_path):
    upper = tmp_path / "AGENTS.md"
    lower = tmp_path / "agents.md"
    mixed = tmp_path / "agents.MD"
    upper.write_text("u\n", encoding="utf-8")
    lower.write_text("l\n", encoding="utf-8")
    mixed.write_text("m\n", encoding="utf-8")

    result = init_vibe(project_root=tmp_path)
    assert result.target_file == upper.resolve()


def test_init_vibe_is_idempotent(tmp_path):
    first = init_vibe(project_root=tmp_path)
    second = init_vibe(project_root=tmp_path)
    assert first.changed is True
    assert second.changed is False
    assert second.action == "unchanged"


def test_init_vibe_project_root_override(tmp_path):
    root = tmp_path / "demo-project"
    root.mkdir()

    result = init_vibe(project_root=root)
    assert result.target_file == (root / "AGENTS.md").resolve()
    assert (root / "AGENTS.md").exists()


def test_init_vibe_agents_file_override(tmp_path):
    result = init_vibe(
        project_root=tmp_path,
        agents_file="docs/agents/custom-agents.md",
    )
    target = tmp_path / "docs" / "agents" / "custom-agents.md"
    assert result.target_file == target.resolve()
    assert target.exists()


def test_show_vibe_outputs_bilingual_webcoding_template():
    text = show_vibe(profile="webcoding", language="bilingual")
    assert START_MARKER in text
    assert END_MARKER in text
    assert "## ztxexp Agent 使用约定" in text
    assert "## ztxexp Agent Guidelines" in text


def test_remove_vibe_removes_managed_block_only(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.write_text(
        "custom-top\n\n" + show_vibe(profile="webcoding", language="en") + "\ncustom-bottom\n",
        encoding="utf-8",
    )

    result = remove_vibe(project_root=tmp_path)
    assert result.action == "removed"
    assert result.changed is True

    content = target.read_text(encoding="utf-8")
    assert "custom-top" in content
    assert "custom-bottom" in content
    assert START_MARKER not in content
    assert END_MARKER not in content


def test_remove_vibe_no_block_is_safe(tmp_path):
    target = tmp_path / "AGENTS.md"
    target.write_text("only-custom\n", encoding="utf-8")

    result = remove_vibe(project_root=tmp_path)
    assert result.action == "no_block"
    assert result.changed is False
    assert target.read_text(encoding="utf-8") == "only-custom\n"


def test_language_and_profile_variants():
    zh_text = show_vibe(profile="codex", language="zh")
    en_text = show_vibe(profile="codex", language="en")
    bilingual_text = show_vibe(profile="codex", language="bilingual")

    assert "Profile: `codex`" in zh_text
    assert "Profile: `codex`" in en_text
    assert "Profile: `codex`" in bilingual_text

    assert "Agent 使用约定" in zh_text
    assert "Agent Guidelines" not in zh_text
    assert "Agent Guidelines" in en_text
    assert "Agent 使用约定" not in en_text
    assert "Agent 使用约定" in bilingual_text and "Agent Guidelines" in bilingual_text


def test_python_m_ztxexp_entrypoint():
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-m", "ztxexp", "show-vibe", "--profile", "webcoding", "--language", "en"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert START_MARKER in completed.stdout
    assert "Agent Guidelines" in completed.stdout


def test_version_bump_consistency():
    repo_root = Path(__file__).resolve().parents[1]
    pyproject_path = repo_root / "pyproject.toml"
    parsed = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    assert parsed["project"]["version"] == "1.0.2"
    assert ztxexp.__version__ == "1.0.2"
