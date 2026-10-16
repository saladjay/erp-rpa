# -*- coding: utf-8 -*-
import os
import threading
import time
from types import SimpleNamespace

from PIL import Image

import recorder
from common.events import Event, read_events
from common.windowinfo import WindowInfo
from recorder import Recorder


def _win(cls):
    return WindowInfo(title="t", class_name=cls, left=0, top=0, right=1, bottom=1)


def _fake_grab():
    return Image.new("RGB", (4, 4), (255, 0, 0))


class _VkKey(object):
    """无 name、无 char 的 KeyCode 替身(如部分 IME 按键)。"""
    vk = 144


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


def test_normalize_key_unmapped_control_chars():
    # 字母区(0x01-0x1A)之外的垃圾控制字符 → 占位,不进时间线
    for ch in ("\x00", "\x1b", "\x1c", "\x1f", "\x7f"):
        assert Recorder.normalize_key(ch) == "ctrl+?_unmapped"
    assert Recorder.normalize_key("enter") == "enter"


def test_record_queued_writer_persists(tmp_path, monkeypatch):
    # 回调线程只抓屏入队;PNG 编码/写盘/jsonl/index 全在写线程
    monkeypatch.setattr(recorder, "ImageGrab",
                        SimpleNamespace(grab=_fake_grab))
    monkeypatch.setattr(recorder, "foreground_window_info",
                        lambda: _win("Notepad"))
    r = Recorder(str(tmp_path))
    r.t0 = time.time()
    w = threading.Thread(target=r._writer, daemon=True)
    w.start()
    r._record(Event(index=0, t=0.1, type="click", x=10, y=20, button="left"))
    r._record(Event(index=1, t=0.2, type="key", key="a"))
    r.q.put(None)
    w.join(timeout=5)
    assert not w.is_alive()
    events = read_events(str(tmp_path))
    assert len(events) == 2
    assert [e.index for e in events] == [0, 1]
    assert events[0].screenshot == "shot_000.png"
    assert events[1].screenshot == "shot_001.png"
    assert os.path.exists(os.path.join(str(tmp_path), "shot_000.png"))
    assert os.path.exists(os.path.join(str(tmp_path), "shot_001.png"))
    assert r.index == 2
    assert r.writer_error is None


def test_writer_error_recorded_not_silent(tmp_path):
    # 写盘失败(session_dir 不存在):writer_error 记录异常并退出,不无声死
    bad = os.path.join(str(tmp_path), "no_such_dir")
    r = Recorder(bad)
    r.q.put((Event(index=0, t=0.0, type="key", key="a"), _fake_grab()))
    r.q.put(None)
    r._writer()                             # 直接在当前线程跑,同步断言
    assert r.writer_error is not None
    assert not os.path.exists(bad)


def test_on_press_vk_fallback_without_name(tmp_path):
    # 无 name 的 KeyCode 不再 AttributeError 崩监听器,记 vk 占位
    r = Recorder(str(tmp_path))
    r.t0 = time.time()
    seen = []
    r._record = seen.append                 # 只验证按键归类,不真入队
    r.on_press(_VkKey())
    assert len(seen) == 1
    assert seen[0].type == "key"
    assert seen[0].key == "vk_144"
