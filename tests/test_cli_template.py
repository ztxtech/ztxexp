from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import ztxexp.cli as cli
from ztxexp.cli import build_parser
from ztxexp.template_wizard import TEMPLATE_MARKER_FILENAME


def _run_interactive(
    tmp_path: Path,
    monkeypatch,
    answers: list[str],
) -> int:
    iterator = iter(answers)
    monkeypatch.setattr(cli, "is_template_interactive_terminal", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _: next(iterator))
    return cli.main(["init-template", "--project-root", str(tmp_path)])


def test_cli_help_contains_init_template():
    parser = build_parser()
    help_text = parser.format_help()
    assert "init-template" in help_text


def test_init_template_interactive_default_flow(tmp_path, monkeypatch):
    rc = _run_interactive(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        answers=[
            "demo_flow",  # experiment_name
            "",  # ablation default: no
            "",  # models default: yes
            "",  # modules default: 1,2,3,4
            "",  # custom modules none
            "",  # mode default: sequential
            "",  # metric mode default: final_plus_stream
            "",  # tracker default: jsonl
        ],
    )
    assert rc == 0
    template_dir = tmp_path / "experiments" / "demo_flow"
    assert (template_dir / "main_experiment.py").exists()
    assert (template_dir / "configs" / "base.json").exists()
    assert (template_dir / "artifacts" / ".gitkeep").exists()
    assert (template_dir / "models" / ".gitkeep").exists()


def test_init_template_includes_ablation_branch_when_enabled(tmp_path, monkeypatch):
    rc = _run_interactive(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        answers=[
            "ablation_case",
            "y",
            "y",
            "1,2,3,4",
            "",
            "1",
            "2",
            "2",
        ],
    )
    assert rc == 0
    script = (tmp_path / "experiments" / "ablation_case" / "main_experiment.py").read_text(
        encoding="utf-8"
    )
    assert "ablation_branch" in script
    assert "use_optional_block" in script


def test_init_template_generates_models_dir_when_enabled(tmp_path):
    rc = cli.main(
        [
            "init-template",
            "--project-root",
            str(tmp_path),
            "--name",
            "with_models",
            "--no-interactive",
        ]
    )
    assert rc == 0
    assert (tmp_path / "experiments" / "with_models" / "models" / ".gitkeep").exists()


def test_init_template_generates_selected_modules_and_custom_modules(tmp_path, monkeypatch):
    rc = _run_interactive(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        answers=[
            "module_mix",
            "n",
            "y",
            "1,6",
            "feature_store, post_process",
            "1",
            "2",
            "2",
        ],
    )
    assert rc == 0
    module_root = tmp_path / "experiments" / "module_mix" / "modules"
    assert (module_root / "data" / "__init__.py").exists()
    assert (module_root / "deploy" / "__init__.py").exists()
    assert (module_root / "feature_store" / "__init__.py").exists()
    assert (module_root / "post_process" / "__init__.py").exists()

    script = (tmp_path / "experiments" / "module_mix" / "main_experiment.py").read_text(
        encoding="utf-8"
    )
    assert "module_data(ctx)" in script
    assert "module_deploy(ctx)" in script
    assert "module_feature_store(ctx)" in script
    assert "module_post_process(ctx)" in script


def test_init_template_inserts_log_metric_for_stream_mode(tmp_path):
    rc = cli.main(
        [
            "init-template",
            "--project-root",
            str(tmp_path),
            "--name",
            "stream_metrics",
            "--no-interactive",
        ]
    )
    assert rc == 0
    script = (tmp_path / "experiments" / "stream_metrics" / "main_experiment.py").read_text(
        encoding="utf-8"
    )
    assert "ctx.log_metric(" in script


def test_init_template_inserts_tracker_when_selected(tmp_path, monkeypatch):
    rc = _run_interactive(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        answers=[
            "tracker_case",
            "n",
            "y",
            "",
            "",
            "1",
            "2",
            "3",  # mlflow
        ],
    )
    assert rc == 0
    script = (tmp_path / "experiments" / "tracker_case" / "main_experiment.py").read_text(
        encoding="utf-8"
    )
    assert 'pipeline.track(\n        "mlflow"' in script


def test_init_template_dry_run_no_files_written(tmp_path):
    rc = cli.main(
        [
            "init-template",
            "--project-root",
            str(tmp_path),
            "--name",
            "dry_run_case",
            "--no-interactive",
            "--dry-run",
        ]
    )
    assert rc == 0
    assert not (tmp_path / "experiments" / "dry_run_case").exists()


def test_init_template_no_interactive_requires_required_args(tmp_path):
    rc = cli.main(
        [
            "init-template",
            "--project-root",
            str(tmp_path),
            "--no-interactive",
        ]
    )
    assert rc == 1


def test_init_template_force_overwrite_behavior(tmp_path):
    target_dir = tmp_path / "experiments" / "overwrite_case"
    target_dir.mkdir(parents=True)
    (target_dir / "main_experiment.py").write_text("custom\n", encoding="utf-8")

    rc_fail = cli.main(
        [
            "init-template",
            "--project-root",
            str(tmp_path),
            "--name",
            "overwrite_case",
            "--no-interactive",
        ]
    )
    assert rc_fail == 1
    assert (target_dir / "main_experiment.py").read_text(encoding="utf-8") == "custom\n"

    rc_ok = cli.main(
        [
            "init-template",
            "--project-root",
            str(tmp_path),
            "--name",
            "overwrite_case",
            "--no-interactive",
            "--force",
        ]
    )
    assert rc_ok == 0
    assert (target_dir / TEMPLATE_MARKER_FILENAME).exists()
    assert "Generated by `ztxexp init-template`" in (target_dir / "main_experiment.py").read_text(
        encoding="utf-8"
    )


def test_init_template_soft_prereq_warning_does_not_block(tmp_path, capsys):
    rc = cli.main(
        [
            "init-template",
            "--project-root",
            str(tmp_path),
            "--name",
            "soft_prereq_case",
            "--no-interactive",
        ]
    )
    assert rc == 0
    output = capsys.readouterr().out
    assert "ztxexp init-vibe" in output
    assert "ztxexp init-skill" in output
    assert (tmp_path / "experiments" / "soft_prereq_case" / "main_experiment.py").exists()


def test_python_m_ztxexp_init_template_entrypoint(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "ztxexp",
            "init-template",
            "--project-root",
            str(tmp_path),
            "--name",
            "entrypoint_case",
            "--no-interactive",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert (tmp_path / "experiments" / "entrypoint_case" / "main_experiment.py").exists()
