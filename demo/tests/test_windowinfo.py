import ctypes
import sys

import pytest

from common.windowinfo import (
    WindowInfo,
    set_dpi_aware,
    window_info_from_hwnd,
)

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="仅 Windows")


def test_window_info_from_hwnd_desktop():
    hwnd = ctypes.windll.user32.GetDesktopWindow()
    info = window_info_from_hwnd(hwnd)
    assert isinstance(info, WindowInfo)
    assert info.right > info.left and info.bottom > info.top


def test_window_info_from_hwnd_invalid():
    assert window_info_from_hwnd(0) is None


def test_set_dpi_aware_callable_and_idempotent():
    set_dpi_aware()
    set_dpi_aware()
