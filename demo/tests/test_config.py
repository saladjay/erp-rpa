import json

import pytest

from common.config import load_config


def test_load_config_reads_json(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"vlm": {"api_key": "k"}}), encoding="utf-8")
    assert load_config(str(tmp_path)) == {"vlm": {"api_key": "k"}}


def test_load_config_reads_bom_json(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"vlm": {"api_key": "k"}}), encoding="utf-8-sig")
    assert load_config(str(tmp_path)) == {"vlm": {"api_key": "k"}}


def test_load_config_copies_example_then_raises(tmp_path):
    (tmp_path / "config.example.json").write_text(
        json.dumps({"vlm": {"api_key": "填我"}}), encoding="utf-8")
    with pytest.raises(RuntimeError) as ei:
        load_config(str(tmp_path))
    assert "api_key" in str(ei.value)
    assert (tmp_path / "config.json").exists()
    assert json.loads((tmp_path / "config.json").read_text(encoding="utf-8")) == json.loads(
        (tmp_path / "config.example.json").read_text(encoding="utf-8"))


def test_load_config_missing_all(tmp_path):
    with pytest.raises(RuntimeError) as ei:
        load_config(str(tmp_path))
    assert "缺少" in str(ei.value)
