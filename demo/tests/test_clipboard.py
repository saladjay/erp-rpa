import ctypes
import sys

import pytest

from common.clipboard import set_text

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="仅 Windows")


def _clipboard_text():
    u32 = ctypes.windll.user32
    k32 = ctypes.windll.kernel32
    u32.OpenClipboard(0)
    try:
        h = u32.GetClipboardData(13)  # CF_UNICODETEXT
        if not h:
            return None
        p = k32.GlobalLock(h)
        s = ctypes.wstring_at(p)
        k32.GlobalUnlock(h)
        return s
    finally:
        u32.CloseClipboard()


def test_set_text_roundtrip():
    assert set_text("你好ABC123")
    assert _clipboard_text() == "你好ABC123"
