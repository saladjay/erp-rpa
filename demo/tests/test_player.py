from common.player import execute_script, find_window, resolve_abs

SCRIPT = {
    "name": "t",
    "target": {"title_re": "x"},
    "steps": [
        {"action": "click", "locator": {"strategy": "offset", "x": 1, "y": 2}},
        {"action": "wait", "seconds": 0.3},
        {"action": "input", "text": "你好"},
    ],
}


def test_find_window_regex():
    wins = [("无标题 - 记事本", 10, 20), ("Chrome", 0, 0)]
    assert find_window("记事本|Notepad", wins) == ("无标题 - 记事本", 10, 20)
    assert find_window("不存在的", wins) is None


def test_resolve_abs():
    assert resolve_abs(100, 200, {"x": 5, "y": 10}) == (105, 210)


class FakeExecutor(object):
    def __init__(self):
        self.calls = []

    def click(self, x, y):
        self.calls.append(("click", x, y))

    def input_text(self, text):
        self.calls.append(("input", text))

    def hotkey(self, keys):
        self.calls.append(("hotkey", tuple(keys)))


def test_execute_script_order_and_wait():
    slept = []
    ex = FakeExecutor()
    log, failed = execute_script(SCRIPT, ("t", 10, 20), ex,
                                 sleep=lambda s: slept.append(s))
    assert failed is None
    assert ex.calls[0] == ("click", 11, 22)
    assert ex.calls[1] == ("input", "你好")
    assert slept == [0.3]
    assert all(e["ok"] for e in log)


def test_execute_script_stops_on_error():
    class Boom(FakeExecutor):
        def input_text(self, text):
            raise RuntimeError("输入失败")

    log, failed = execute_script(SCRIPT, ("t", 0, 0), Boom())
    assert failed == 2
    assert log[-1]["ok"] is False and "输入失败" in log[-1]["error"]
