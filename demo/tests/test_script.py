from common.script import validate

VALID = {
    "name": "notepad-demo",
    "target": {"title_re": "记事本|Notepad"},
    "steps": [
        {"action": "click", "locator": {"strategy": "offset", "x": 100, "y": 60},
         "desc": "点编辑区"},
        {"action": "input", "text": "你好", "desc": "输入"},
        {"action": "hotkey", "keys": ["ctrl", "s"], "desc": "保存"},
        {"action": "wait", "seconds": 0.5, "desc": "等"},
    ],
}


def test_valid_script():
    assert validate(VALID) == []


def test_not_dict():
    assert validate([1, 2]) == ["脚本必须是 JSON 对象"]


def test_missing_name_and_target():
    errs = validate({"steps": VALID["steps"]})
    assert any("name" in e for e in errs)
    assert any("title_re" in e for e in errs)


def test_empty_steps():
    errs = validate(dict(VALID, steps=[]))
    assert any("steps" in e for e in errs)


def test_unknown_action():
    bad = dict(VALID, steps=[{"action": "scroll", "locator": {}}])
    assert any("action" in e for e in validate(bad))


def test_click_needs_int_locator():
    bad = dict(VALID, steps=[{"action": "click",
                              "locator": {"strategy": "offset", "x": "a", "y": 1}}])
    errs = validate(bad)
    assert any("x" in e for e in errs)


def test_input_needs_text():
    bad = dict(VALID, steps=[{"action": "input"}])
    assert any("text" in e for e in validate(bad))


def test_hotkey_needs_keys():
    bad = dict(VALID, steps=[{"action": "hotkey", "keys": []}])
    assert any("keys" in e for e in validate(bad))


def test_wait_needs_positive_seconds():
    bad = dict(VALID, steps=[{"action": "wait", "seconds": 0}])
    assert any("seconds" in e for e in validate(bad))
