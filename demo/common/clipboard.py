# -*- coding: utf-8 -*-
"""剪贴板写入(ctypes,始终以 32 位 Python 运行,指针截断无忧)。"""
import ctypes

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
_user32 = ctypes.windll.user32
_kernel32 = ctypes.windll.kernel32


def set_text(text):
    """文本写入剪贴板,成功返回 True。"""
    if not _user32.OpenClipboard(0):
        return False
    try:
        _user32.EmptyClipboard()
        data = text.encode("utf-16-le") + b"\x00\x00"
        h = _kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        if not h:
            return False
        p = _kernel32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        _kernel32.GlobalUnlock(h)
        return bool(_user32.SetClipboardData(CF_UNICODETEXT, h))
    finally:
        _user32.CloseClipboard()
