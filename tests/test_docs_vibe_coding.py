from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_vibe_coding_doc_contains_required_sections():
    doc_path = ROOT / "docs_src" / "vibe-coding.zh.md"
    assert doc_path.exists()

    content = doc_path.read_text(encoding="utf-8")
    required_keywords = [
        "init-vibe",
        "init-skill",
        "init-template",
        "skills/",
        ".codex/skills/",
        "run.json.status",
        "skipped_unmanaged",
        "remove-skill",
    ]
    for keyword in required_keywords:
        assert keyword in content
