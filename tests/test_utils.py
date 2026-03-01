from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from ztxexp import utils


@dataclass
class _DemoCfg:
    lr: float
    seed: int


def test_as_plain_dict_supports_mapping_dataclass_and_namespace():
    assert utils.as_plain_dict({"lr": 0.001}) == {"lr": 0.001}
    assert utils.as_plain_dict(_DemoCfg(lr=0.01, seed=42)) == {"lr": 0.01, "seed": 42}
    assert utils.as_plain_dict(SimpleNamespace(model="tiny")) == {"model": "tiny"}

    with pytest.raises(TypeError):
        utils.as_plain_dict(123)


def test_flatten_unflatten_roundtrip():
    data = {
        "model": {"name": "tiny", "layers": 12},
        "lr": 0.001,
        "seed": 42,
    }
    flat = utils.flatten_dict(data)
    assert flat["model.name"] == "tiny"
    assert flat["model.layers"] == 12

    restored = utils.unflatten_dict(flat)
    assert restored == data


def test_unflatten_detects_key_conflict():
    with pytest.raises(ValueError):
        utils.unflatten_dict({"a": 1, "a.b": 2})


def test_deep_merge_and_diff():
    base = {
        "optimizer": {"type": "adam", "lr": 0.001},
        "batch_size": 32,
    }
    override = {
        "optimizer": {"lr": 0.01, "weight_decay": 1e-4},
        "epochs": 10,
    }
    merged = utils.deep_merge_dicts(base, override)
    assert merged == {
        "optimizer": {"type": "adam", "lr": 0.01, "weight_decay": 1e-4},
        "batch_size": 32,
        "epochs": 10,
    }
    # 确保不会原地修改输入
    assert base["optimizer"]["lr"] == 0.001

    diff = utils.dict_diff(base, merged)
    assert diff["added"]["epochs"] == 10
    assert diff["changed"]["optimizer.lr"]["left"] == 0.001
    assert diff["changed"]["optimizer.lr"]["right"] == 0.01


def test_sanitize_filename_and_build_run_name():
    name = utils.sanitize_filename('model:tiny/lr=1e-3?*', max_length=64)
    assert ":" not in name
    assert "/" not in name
    assert "?" not in name
    assert "*" not in name

    run_name = utils.build_run_name(
        {"model": "tiny", "lr": 0.001, "seed": 42},
        keys=["model", "lr"],
        prefix="exp",
        max_length=60,
        hash_length=6,
    )
    assert run_name.startswith("exp_")
    assert len(run_name) <= 60


def test_split_batches():
    batches = utils.split_batches([1, 2, 3, 4, 5], batch_size=2)
    assert batches == [[1, 2], [3, 4], [5]]

    with pytest.raises(ValueError):
        utils.split_batches([1, 2], batch_size=0)


def test_atomic_write_and_atomic_json(tmp_path):
    text_path = tmp_path / "tmp" / "out.txt"
    utils.write_text_atomic(text_path, "hello")
    assert text_path.read_text(encoding="utf-8") == "hello"

    json_path = tmp_path / "tmp" / "metrics.json"
    payload = {"score": 0.95, "tags": ["baseline"]}
    utils.save_json_atomic(payload, json_path)
    assert json.loads(json_path.read_text(encoding="utf-8")) == payload


def test_jsonl_append_and_load(tmp_path):
    jsonl_path = tmp_path / "events.jsonl"
    utils.append_jsonl(jsonl_path, {"event": "start"})
    utils.append_jsonl(jsonl_path, {"event": "end", "ok": True})
    records = utils.load_jsonl(jsonl_path)
    assert records == [{"event": "start"}, {"event": "end", "ok": True}]


def test_jsonl_load_skip_invalid(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"ok": 1}\nnot_json\n{"ok": 2}\n', encoding="utf-8")

    records = utils.load_jsonl(path, skip_invalid=True)
    assert records == [{"ok": 1}, {"ok": 2}]

    with pytest.raises(json.JSONDecodeError):
        utils.load_jsonl(path, skip_invalid=False)


def test_retry_call_success_and_failure():
    state = {"n": 0}

    def flaky() -> str:
        state["n"] += 1
        if state["n"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    assert utils.retry_call(flaky, max_attempts=5, wait_sec=0.0) == "ok"
    assert state["n"] == 3

    with pytest.raises(RuntimeError):
        utils.retry_call(lambda: (_ for _ in ()).throw(RuntimeError("x")), max_attempts=2)
