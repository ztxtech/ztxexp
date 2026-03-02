"""Interactive template wizard for ``ztxexp init-template``.

This module provides a command-line questionnaire and scaffold generator that
produces a runnable experiment template project.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal

from ztxexp import __version__, utils
from ztxexp.skill import SKILL_NAME
from ztxexp.vibe import END_MARKER, START_MARKER

SUPPORTED_RUN_MODES = ("sequential", "process_pool", "joblib", "dynamic")
SUPPORTED_METRIC_MODES = ("final_only", "final_plus_stream")
SUPPORTED_TRACKERS = ("none", "jsonl", "mlflow", "wandb")

PRESET_MODULES = ("data", "model", "train", "eval", "infer", "deploy")

TEMPLATE_MARKER_FILENAME = ".ztxexp-managed-template.json"

RunMode = Literal["sequential", "process_pool", "joblib", "dynamic"]
MetricMode = Literal["final_only", "final_plus_stream"]
TrackerMode = Literal["none", "jsonl", "mlflow", "wandb"]


@dataclass(slots=True)
class TemplateAnswers:
    """Collected answers for template generation."""

    experiment_name: str
    ablation: bool
    with_models_dir: bool
    modules: list[str]
    mode: RunMode
    metric_mode: MetricMode
    tracker: TrackerMode


@dataclass(slots=True)
class TemplateRenderResult:
    """Template rendering result."""

    template_dir: Path
    action: str
    changed: bool
    dry_run: bool
    warnings: list[str] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)

    def summary_lines(self) -> list[str]:
        """Build summary lines for CLI output."""
        lines = [
            (
                f"template_dir={self.template_dir}, action={self.action}, "
                f"changed={self.changed}, dry_run={self.dry_run}"
            )
        ]
        if self.warnings:
            for warning in self.warnings:
                lines.append(f"warning={warning}")
        if self.files:
            lines.append(f"files={len(self.files)}")
            for file_path in self.files:
                lines.append(f"file={file_path}")
        return lines


def is_interactive_terminal() -> bool:
    """Return whether current stdin/stdout are interactive terminals."""
    return bool(sys.stdin.isatty() and sys.stdout.isatty())


def resolve_project_root(project_root: str | Path | None) -> Path:
    """Resolve and validate project root directory."""
    root = Path.cwd() if project_root is None else Path(project_root)
    root = root.expanduser().resolve()
    if root.exists() and not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")
    if not root.exists():
        raise ValueError(f"project root does not exist: {root}")
    return root


def _sanitize_identifier(value: str, default: str) -> str:
    text = value.strip()
    if not text:
        text = default
    text = text.replace("-", "_").replace(" ", "_")
    cleaned = "".join(ch for ch in text if ch.isalnum() or ch == "_")
    cleaned = cleaned.strip("_")
    if not cleaned:
        return default
    if cleaned[0].isdigit():
        cleaned = f"m_{cleaned}"
    return cleaned.lower()


def _ask_text(
    prompt: str,
    default: str,
    input_fn: Callable[[str], str],
) -> str:
    raw = input_fn(f"{prompt} [默认: {default}] ").strip()
    return raw if raw else default


def _ask_yes_no(
    prompt: str,
    default: bool,
    input_fn: Callable[[str], str],
) -> bool:
    hint = "Y/n" if default else "y/N"
    raw = input_fn(f"{prompt} ({hint}) ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true"}


def _ask_choice(
    title: str,
    options: tuple[str, ...],
    default_index: int,
    input_fn: Callable[[str], str],
) -> str:
    print(title)
    for idx, option in enumerate(options, start=1):
        marker = " (默认)" if idx == default_index else ""
        print(f"  {idx}) {option}{marker}")
    raw = input_fn(f"请输入选项 [1-{len(options)}]: ").strip()
    if not raw:
        return options[default_index - 1]
    if raw.isdigit():
        pos = int(raw)
        if 1 <= pos <= len(options):
            return options[pos - 1]
    if raw in options:
        return raw
    print("输入无效，已回退到默认值。")
    return options[default_index - 1]


def _collect_modules_interactive(input_fn: Callable[[str], str]) -> list[str]:
    print("4) 需要哪些模块？可多选（逗号分隔）")
    for idx, module in enumerate(PRESET_MODULES, start=1):
        default_mark = " (默认)" if idx <= 4 else ""
        print(f"  {idx}) {module}{default_mark}")

    raw = input_fn("请输入预置模块编号（默认 1,2,3,4）: ").strip()
    if not raw:
        picked = ["data", "model", "train", "eval"]
    else:
        picked = []
        for token in raw.split(","):
            item = token.strip()
            if not item:
                continue
            if item.isdigit():
                pos = int(item)
                if 1 <= pos <= len(PRESET_MODULES):
                    picked.append(PRESET_MODULES[pos - 1])
            elif item in PRESET_MODULES:
                picked.append(item)

    custom_raw = input_fn("可选：追加自定义模块（逗号分隔，留空跳过）: ").strip()
    custom = []
    if custom_raw:
        custom = [_sanitize_identifier(token, default="module") for token in custom_raw.split(",")]

    ordered = []
    for module in [*picked, *custom]:
        name = _sanitize_identifier(module, default="module")
        if name not in ordered:
            ordered.append(name)
    return ordered or ["data", "model", "train", "eval"]


def ask_template_questions(
    name: str | None = None,
    yes: bool = False,
    input_fn: Callable[[str], str] | None = None,
) -> TemplateAnswers:
    """Ask interactive questions and return normalized answers.

    Args:
        name: Optional preset experiment name.
        yes: If True, use recommended defaults without prompting.
        input_fn: Input function for testing or custom IO.

    Returns:
        TemplateAnswers: Normalized questionnaire results.
    """
    if input_fn is None:
        input_fn = input

    default_name = _sanitize_identifier(name or "my_experiment", default="my_experiment")
    if yes:
        return TemplateAnswers(
            experiment_name=default_name,
            ablation=False,
            with_models_dir=True,
            modules=["data", "model", "train", "eval"],
            mode="sequential",
            metric_mode="final_plus_stream",
            tracker="jsonl",
        )

    experiment_name = _sanitize_identifier(
        _ask_text("1) 实验名称", default_name, input_fn=input_fn),
        default="my_experiment",
    )
    ablation = _ask_yes_no("2) 是否进行消融实验？", default=False, input_fn=input_fn)
    with_models_dir = _ask_yes_no("3) 是否生成 models 目录？", default=True, input_fn=input_fn)
    modules = _collect_modules_interactive(input_fn=input_fn)
    mode = _ask_choice(
        "5) 执行模式：",
        options=SUPPORTED_RUN_MODES,
        default_index=1,
        input_fn=input_fn,
    )
    metric_mode = _ask_choice(
        "6) 指标记录方式：",
        options=SUPPORTED_METRIC_MODES,
        default_index=2,
        input_fn=input_fn,
    )
    tracker = _ask_choice(
        "7) 追踪器：",
        options=SUPPORTED_TRACKERS,
        default_index=2,
        input_fn=input_fn,
    )

    return TemplateAnswers(
        experiment_name=experiment_name,
        ablation=ablation,
        with_models_dir=with_models_dir,
        modules=modules,
        mode=mode,  # type: ignore[arg-type]
        metric_mode=metric_mode,  # type: ignore[arg-type]
        tracker=tracker,  # type: ignore[arg-type]
    )


def check_init_prerequisites(project_root: Path) -> list[str]:
    """Check optional prerequisites and return warning messages.

    The check is advisory and never blocks template generation.
    """
    warnings: list[str] = []

    vibe_ok = False
    for filename in ("AGENTS.md", "agents.md", "agents.MD"):
        path = project_root / filename
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if START_MARKER in text and END_MARKER in text:
            vibe_ok = True
            break

    if not vibe_ok:
        warnings.append(
            "未检测到 vibe 受管区块，建议先执行: ztxexp init-vibe"
        )

    skill_candidates = [
        project_root / "skills" / SKILL_NAME / "SKILL.md",
        project_root / ".codex" / "skills" / SKILL_NAME / "SKILL.md",
    ]
    if not any(path.exists() for path in skill_candidates):
        warnings.append(
            "未检测到 ztx-exp-manager skill，建议先执行: ztxexp init-skill"
        )

    return warnings


def render_base_config(answers: TemplateAnswers) -> dict[str, object]:
    """Render base config payload for generated template."""
    return {
        "experiment_name": answers.experiment_name,
        "seed": 42,
        "ablation": answers.ablation,
        "with_models_dir": answers.with_models_dir,
        "modules": answers.modules,
        "default_mode": answers.mode,
        "metric_mode": answers.metric_mode,
        "tracker": answers.tracker,
    }


def _render_module_stubs(modules: list[str]) -> tuple[str, str]:
    blocks = []
    calls = []
    for module in modules:
        fn_name = f"module_{_sanitize_identifier(module, default='module')}"
        blocks.append(
            "\n".join(
                [
                    f"def {fn_name}(ctx: RunContext) -> None:",
                    f'    """TODO: implement `{module}` module logic."""',
                    "    _ = ctx",
                    "",
                ]
            )
        )
        calls.append(f"    {fn_name}(ctx)")

    return ("\n".join(blocks).rstrip(), "\n".join(calls) if calls else "    pass")


def _render_tracker_snippet(tracker: TrackerMode, experiment_name: str) -> str:
    if tracker == "none":
        return ""
    if tracker == "jsonl":
        return '    pipeline = pipeline.track("jsonl")\n'
    if tracker == "mlflow":
        return (
            '    pipeline = pipeline.track(\n'
            '        "mlflow",\n'
            f'        experiment_name="{experiment_name}_template",\n'
            "    )\n"
        )
    return (
        '    pipeline = pipeline.track(\n'
        '        "wandb",\n'
        f'        project="{experiment_name}_template",\n'
        "    )\n"
    )


def render_template_script(answers: TemplateAnswers) -> str:
    """Render generated command-line experiment script."""
    module_stubs, module_calls = _render_module_stubs(answers.modules)

    ablation_snippet = ""
    if answers.ablation:
        ablation_snippet = (
            "    pipeline = pipeline.variants([\n"
            '        {"ablation_branch": "baseline", "use_optional_block": True},\n'
            '        {"ablation_branch": "no_optional_block", "use_optional_block": False},\n'
            "    ])\n"
        )

    stream_metric_snippet = ""
    if answers.metric_mode == "final_plus_stream":
        stream_metric_snippet = (
            "    ctx.log_metric(step=1, metrics={\"loss\": 0.88}, split=\"train\", phase=\"fit\")\n"
            "    ctx.log_metric(step=2, metrics={\"loss\": 0.73}, split=\"train\", phase=\"fit\")\n"
        )

    tracker_snippet = _render_tracker_snippet(answers.tracker, answers.experiment_name)
    default_results_root = f"./results_{answers.experiment_name}"

    return f'''"""Generated by `ztxexp init-template`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ztxexp import ExperimentPipeline, ResultAnalyzer, RunContext


{module_stubs}


def exp_fn(ctx: RunContext) -> dict[str, float] | None:
    """Single experiment function."""
    cfg = ctx.config
    lr = float(cfg.get("lr", 0.001))
{stream_metric_snippet}    artifact_path = Path(ctx.run_dir) / "artifacts" / "summary.txt"
    artifact_path.write_text(
        f"run={{ctx.run_id}}, lr={{lr}}\\n",
        encoding="utf-8",
    )

{module_calls}

    score = max(0.0, 1.0 - lr)
    return {{"score": round(score, 4), "latency_ms": round(120 + lr * 1000, 3)}}


def _load_base_config() -> dict[str, Any]:
    config_path = Path(__file__).resolve().parent / "configs" / "base.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


def build_pipeline(results_root: str) -> ExperimentPipeline:
    base_config = _load_base_config()
    pipeline = (
        ExperimentPipeline(results_root=results_root, base_config=base_config)
        .grid({{"lr": [0.001, 0.01]}})
    )
{ablation_snippet}{tracker_snippet}    return pipeline


def run_experiment(results_root: str, mode: str) -> None:
    summary = build_pipeline(results_root=results_root).run(exp_fn, mode=mode)
    print(summary)


def analyze_results(results_root: str, output_csv: str | None) -> None:
    analyzer = ResultAnalyzer(results_root)
    df = analyzer.to_dataframe(statuses=("succeeded",))
    print(df.head(20))
    if output_csv:
        analyzer.to_csv(output_csv, statuses=("succeeded",))


def clean_results(results_root: str, apply_delete: bool) -> None:
    analyzer = ResultAnalyzer(results_root)
    analyzer.clean_results(
        statuses=("failed", "running", "skipped"),
        dry_run=not apply_delete,
        confirm=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generated experiment CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run experiments")
    run_parser.add_argument("--results-root", default="{default_results_root}")
    run_parser.add_argument(
        "--mode",
        choices={list(SUPPORTED_RUN_MODES)},
        default="{answers.mode}",
    )

    analyze_parser = subparsers.add_parser("analyze", help="Analyze experiment results")
    analyze_parser.add_argument("--results-root", default="{default_results_root}")
    analyze_parser.add_argument("--output-csv", default=None)

    clean_parser = subparsers.add_parser("clean", help="Clean failed/skipped/running runs")
    clean_parser.add_argument("--results-root", default="{default_results_root}")
    clean_parser.add_argument("--apply", action="store_true")

    args = parser.parse_args()
    if args.command == "run":
        run_experiment(results_root=args.results_root, mode=args.mode)
        return 0
    if args.command == "analyze":
        analyze_results(results_root=args.results_root, output_csv=args.output_csv)
        return 0
    if args.command == "clean":
        clean_results(results_root=args.results_root, apply_delete=args.apply)
        return 0
    parser.error(f"Unknown command: {{args.command}}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''


def build_template_plan(
    answers: TemplateAnswers,
    project_root: Path,
    output_dir: str | Path | None = None,
) -> dict[str, object]:
    """Build scaffold plan from answers."""
    if output_dir is None:
        out_root = project_root / "experiments"
    else:
        candidate = Path(output_dir).expanduser()
        out_root = candidate if candidate.is_absolute() else project_root / candidate

    out_root = out_root.resolve()
    template_dir = (out_root / answers.experiment_name).resolve()

    return {
        "project_root": project_root,
        "output_root": out_root,
        "template_dir": template_dir,
    }


def _is_managed_template(target_dir: Path) -> bool:
    marker = utils.load_json(target_dir / TEMPLATE_MARKER_FILENAME)
    if not marker:
        return False
    return (
        marker.get("installed_by") == "ztxexp init-template"
        and marker.get("experiment_name") == target_dir.name
    )


def _render_marker(answers: TemplateAnswers) -> str:
    payload = {
        "installed_by": "ztxexp init-template",
        "version": __version__,
        "experiment_name": answers.experiment_name,
        "created_at": utils.utc_now_iso(),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def create_template_scaffold(
    plan: dict[str, object],
    answers: TemplateAnswers,
    dry_run: bool = False,
    force: bool = False,
    warnings: list[str] | None = None,
) -> TemplateRenderResult:
    """Create template scaffold according to plan and answers."""
    template_dir = Path(plan["template_dir"])  # type: ignore[arg-type]
    existed = template_dir.exists()

    if existed and not _is_managed_template(template_dir) and not force:
        raise ValueError(
            f"Template directory exists and is unmanaged: {template_dir}. "
            "Use --force to overwrite generated files."
        )

    base_config_payload = (
        json.dumps(render_base_config(answers), ensure_ascii=False, indent=2) + "\n"
    )
    main_script = render_template_script(answers)
    marker_payload = _render_marker(answers)

    files_to_write: dict[Path, str] = {
        template_dir / "main_experiment.py": main_script,
        template_dir / "configs" / "base.json": base_config_payload,
        template_dir / "artifacts" / ".gitkeep": "",
        template_dir / "modules" / "__init__.py": "",
        template_dir / TEMPLATE_MARKER_FILENAME: marker_payload,
    }

    if answers.with_models_dir:
        files_to_write[template_dir / "models" / ".gitkeep"] = ""

    for module in answers.modules:
        module_name = _sanitize_identifier(module, default="module")
        files_to_write[template_dir / "modules" / module_name / "__init__.py"] = (
            f'"""Module stub for `{module_name}`."""\n'
        )

    changed_files: list[Path] = []
    for path, content in files_to_write.items():
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            changed_files.append(path)

    changed = bool(changed_files) or not existed
    if not changed:
        action = "unchanged"
    else:
        action = "create" if not existed else "update"
        if dry_run:
            action = f"would_{action}"

    if changed and not dry_run:
        for path, content in files_to_write.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    return TemplateRenderResult(
        template_dir=template_dir,
        action=action,
        changed=changed,
        dry_run=dry_run,
        warnings=list(warnings or []),
        files=sorted(files_to_write.keys()),
    )
