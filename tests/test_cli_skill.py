from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import ztxexp.cli as cli
from ztxexp.cli import build_parser
from ztxexp.skill import (
    choose_target_mode_interactive,
    init_skill,
    remove_skill,
    render_openai_yaml,
    render_skill_markdown,
    show_skill,
)


def _normalize_newline(value: str) -> str:
    return value.replace("\r\n", "\n")


def test_cli_help_contains_skill_subcommands():
    parser = build_parser()
    help_text = parser.format_help()
    assert "init-skill" in help_text
    assert "show-skill" in help_text
    assert "remove-skill" in help_text


def test_show_skill_outputs_markdown():
    text = show_skill(language="bilingual")
    assert "name: ztx-exp-manager" in text
    assert "ExperimentPipeline" in text
    assert 'run.json.status == "succeeded"' in text


def test_builtin_skill_templates_match_repository_files():
    repo_root = Path(__file__).resolve().parents[1]
    skill_md_path = repo_root / "skills" / "ztx-exp-manager" / "SKILL.md"
    openai_yaml_path = repo_root / "skills" / "ztx-exp-manager" / "agents" / "openai.yaml"

    assert skill_md_path.exists()
    assert openai_yaml_path.exists()

    skill_md_content = _normalize_newline(skill_md_path.read_text(encoding="utf-8"))
    openai_yaml_content = _normalize_newline(openai_yaml_path.read_text(encoding="utf-8"))

    assert skill_md_content == render_skill_markdown(language="bilingual")
    assert openai_yaml_content == render_openai_yaml()


def test_init_skill_interactive_choice_1_skills_only(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "1")
    assert choose_target_mode_interactive() == "skills"


def test_init_skill_interactive_choice_2_codex_only(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "2")
    assert choose_target_mode_interactive() == "codex"


def test_init_skill_interactive_choice_3_both_targets(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "3")
    assert choose_target_mode_interactive() == "both"


def test_init_skill_target_arg_bypasses_prompt(tmp_path, monkeypatch):
    def _should_not_call():
        raise RuntimeError("interactive prompt should not be called")

    monkeypatch.setattr(cli, "choose_target_mode_interactive", _should_not_call)
    rc = cli.main(
        [
            "init-skill",
            "--project-root",
            str(tmp_path),
            "--target",
            "codex",
            "--language",
            "zh",
        ]
    )
    assert rc == 0
    assert (tmp_path / ".codex" / "skills" / "ztx-exp-manager" / "SKILL.md").exists()


def test_init_skill_non_interactive_defaults_to_skills(tmp_path):
    rc = cli.main(["init-skill", "--project-root", str(tmp_path), "--no-interactive"])
    assert rc == 0
    assert (tmp_path / "skills" / "ztx-exp-manager" / "SKILL.md").exists()


def test_init_skill_idempotent(tmp_path):
    first = init_skill(project_root=tmp_path, target_mode="skills", language="bilingual")
    second = init_skill(project_root=tmp_path, target_mode="skills", language="bilingual")

    assert first.results[0].changed is True
    assert second.results[0].changed is False
    assert second.results[0].action == "unchanged"


def test_init_skill_unmanaged_dir_skipped_without_force(tmp_path):
    target = tmp_path / "skills" / "ztx-exp-manager"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("custom skill\n", encoding="utf-8")

    result = init_skill(project_root=tmp_path, target_mode="skills", force=False)
    assert result.results[0].action == "skipped_unmanaged"
    assert (target / "SKILL.md").read_text(encoding="utf-8") == "custom skill\n"


def test_init_skill_force_overwrites_unmanaged(tmp_path):
    target = tmp_path / "skills" / "ztx-exp-manager"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("custom skill\n", encoding="utf-8")

    result = init_skill(project_root=tmp_path, target_mode="skills", force=True)
    assert result.results[0].action == "update"

    content = (target / "SKILL.md").read_text(encoding="utf-8")
    assert "name: ztx-exp-manager" in content
    assert (target / ".ztxexp-managed-skill.json").exists()


def test_remove_skill_only_removes_managed(tmp_path):
    init_skill(project_root=tmp_path, target_mode="skills")

    unmanaged = tmp_path / ".codex" / "skills" / "ztx-exp-manager"
    unmanaged.mkdir(parents=True)
    (unmanaged / "SKILL.md").write_text("custom\n", encoding="utf-8")

    result = remove_skill(project_root=tmp_path, target_mode="both")

    actions = {item.target_dir: item.action for item in result.results}
    managed_target = tmp_path / "skills" / "ztx-exp-manager"
    unmanaged_target = tmp_path / ".codex" / "skills" / "ztx-exp-manager"

    assert actions[managed_target] == "removed"
    assert actions[unmanaged_target] == "skipped_unmanaged"
    assert not managed_target.exists()
    assert unmanaged_target.exists()


def test_remove_skill_safe_when_missing(tmp_path):
    result = remove_skill(project_root=tmp_path, target_mode="both")
    assert all(item.action == "not_found" for item in result.results)
    assert all(item.changed is False for item in result.results)


def test_remove_skill_dry_run_no_mutation(tmp_path):
    init_skill(project_root=tmp_path, target_mode="skills")
    target = tmp_path / "skills" / "ztx-exp-manager"

    result = remove_skill(project_root=tmp_path, target_mode="skills", dry_run=True)
    assert result.results[0].action == "would_remove"
    assert target.exists()


def test_python_m_ztxexp_show_skill_entrypoint():
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [sys.executable, "-m", "ztxexp", "show-skill", "--language", "en"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "name: ztx-exp-manager" in completed.stdout
    assert "Core Rules" in completed.stdout
