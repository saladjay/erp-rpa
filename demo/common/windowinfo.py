# -*- coding: utf-8 -*-
"""前台窗口信息抓取(ctypes + user32,Win7/Win11 通用)。"""
import ctypes
from ctypes import wintypes
from dataclasses import asdict, dataclass

_user32 = ctypes.windll.user32


@dataclass
class WindowInfo:
    title: str
    class_name: str
    left: int
    top: int
    right: int
    bottom: int

    def as_dict(self):
        return asdict(self)


def window_info_from_hwnd(hwnd):
    if not hwnd:
        return None
    length = _user32.GetWindowTextLengthW(hwnd)
    title_buf = ctypes.create_unicode_buffer(length + 1)
    _user32.GetWindowTextW(hwnd, title_buf, length + 1)
    class_buf = ctypes.create_unicode_buffer(256)
    _user32.GetClassNameW(hwnd, class_buf, 256)
    rect = wintypes.RECT()
    if not _user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return None
    return WindowInfo(title=title_buf.value, class_name=class_buf.value,
                      left=rect.left, top=rect.top,
                      right=rect.right, bottom=rect.bottom)


def foreground_window_info():
    return window_info_from_hwnd(_user32.GetForegroundWindow())
