from common.windowinfo import WindowInfo
from recorder import Recorder


def _win(cls):
    return WindowInfo(title="t", class_name=cls, left=0, top=0, right=1, bottom=1)


def test_skip_console_windows():
    r = Recorder.__new__(Recorder)          # 不跑 __init__,只测纯逻辑
    assert r._skip(_win("ConsoleWindowClass")) is True
    assert r._skip(_win("CASCADIA_HOSTING_WINDOW_CLASS")) is True
    assert r._skip(_win("Notepad")) is False
    assert r._skip(None) is True


def test_normalize_key_maps_control_chars():
    # 协调人补充2:Windows 下 pynput 把 ctrl+s 报成控制字符 \x13,须映射成 ctrl+s
    assert Recorder.normalize_key("\x13") == "ctrl+s"
    assert Recorder.normalize_key("\x01") == "ctrl+a"
    assert Recorder.normalize_key("a") == "a"
    assert Recorder.normalize_key(" ") == " "
