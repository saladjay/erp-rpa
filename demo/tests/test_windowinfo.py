import sys

import pytest

from common.windowinfo import WindowInfo, window_info_from_hwnd

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="仅 Windows")


def test_window_info_from_hwnd_desktop():
    import ctypes
    hwnd = ctypes.windll.user32.GetDesktopWindow()
    info = window_info_from_hwnd(hwnd)
    assert isinstance(info, WindowInfo)
    assert info.right > info.left and info.bottom > info.top
