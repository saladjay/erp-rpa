import sys
import types

from common.player import execute_script, find_window, resolve_abs

SCRIPT = {
    "name": "t",
    "target": {"title_re": "x"},
    "steps": [
        {"action": "click", "locator": {"strategy": "offset", "x": 1, "y": 2},
         "desc": "测试步骤"},
        {"action": "wait", "seconds": 0.3, "desc": "测试步骤"},
        {"action": "input", "text": "你好", "desc": "测试步骤"},
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


def test_execute_script_keyboard_interrupt_forensics():
    class Interrupt(FakeExecutor):
        def input_text(self, text):
            raise KeyboardInterrupt()

    log, failed = execute_script(SCRIPT, ("t", 0, 0), Interrupt())
    assert failed == 2
    assert log[-1]["ok"] is False
    assert "中断" in log[-1]["error"]
    assert log[-1]["desc"] == "测试步骤"


def test_log_entries_carry_desc():
    log, failed = execute_script(SCRIPT, ("t", 0, 0), FakeExecutor())
    assert failed is None
    assert [e["desc"] for e in log] == ["测试步骤"] * 3


def _fake_pywinauto(monkeypatch, windows):
    """注入假 pywinauto 模块;windows(visible_only=...) 由调用方决定返回值。"""
    import common.player as player_mod

    class FakeDesktop(object):
        def __init__(self, backend=None):
            assert backend == "win32"

        def windows(self, visible_only=False):
            assert visible_only is True
            return windows

    mod = types.ModuleType("pywinauto")
    mod.Desktop = FakeDesktop
    monkeypatch.setitem(sys.modules, "pywinauto", mod)
    return player_mod


def test_focus_window(monkeypatch):
    focused = []

    class FakeWin(object):
        def __init__(self, title):
            self._title = title

        def window_text(self):
            return self._title

        def set_focus(self):
            focused.append(self._title)

    player_mod = _fake_pywinauto(
        monkeypatch, [FakeWin("无标题 - 记事本"), FakeWin("Chrome")])

    assert player_mod.focus_window("记事本") is True
    assert focused == ["无标题 - 记事本"]
    assert player_mod.focus_window("不存在的") is False
    assert focused == ["无标题 - 记事本"]  # 未匹配不聚焦


def test_enumerate_windows_skips_minimized(monkeypatch):
    class Rect(object):
        def __init__(self, left, top):
            self.left = left
            self.top = top

    class FakeWin(object):
        def __init__(self, title, left, top, minimized=False, boom=False):
            self._title = title
            self._left = left
            self._top = top
            self._minimized = minimized
            self._boom = boom

        def window_text(self):
            return self._title

        def rectangle(self):
            if self._boom:
                raise RuntimeError("rect 失败")
            return Rect(self._left, self._top)

        def is_minimized(self):
            return self._minimized

    player_mod = _fake_pywinauto(monkeypatch, [
        FakeWin("正常", 10, 20),
        FakeWin("最小化", -32000, -32000, minimized=True),
        FakeWin("异常", 1, 1, boom=True),
    ])

    assert player_mod.enumerate_windows() == [("正常", 10, 20)]
