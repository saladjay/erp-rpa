# -*- coding: utf-8 -*-
"""用法: python player.py sessions/xxx/script.json [--dry-run]"""
import argparse
import ctypes
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.player import enumerate_windows, execute_script, find_window
from common.script import validate
from common.windowinfo import set_dpi_aware  # 补充1:启动即 DPI 感知


def alert(msg):
    ctypes.windll.user32.MessageBoxW(0, msg, u"RPA 回放", 0x30)


_SPECIAL_KEYS = None


def _special_map():
    global _SPECIAL_KEYS
    if _SPECIAL_KEYS is None:
        from pynput.keyboard import Key
        _SPECIAL_KEYS = {
            "ctrl": Key.ctrl, "ctrl_l": Key.ctrl_l, "ctrl_r": Key.ctrl_r,
            "alt": Key.alt, "shift": Key.shift, "enter": Key.enter,
            "esc": Key.esc, "tab": Key.tab, "space": Key.space,
            "backspace": Key.backspace, "delete": Key.delete,
            "up": Key.up, "down": Key.down, "left": Key.left, "right": Key.right,
            "home": Key.home, "end": Key.end, "pagedown": Key.page_down,
            "pageup": Key.page_up, "f4": Key.f4, "f5": Key.f5, "f12": Key.f12,
        }
    return _SPECIAL_KEYS


class RealExecutor(object):
    """pynput 执行器;中文经剪贴板粘贴(输入法无关,Win7/Win11 通用)。"""

    def __init__(self):
        from pynput.keyboard import Controller as KeyController
        from pynput.mouse import Button, Controller as MouseController
        from common.clipboard import set_text
        self._set_text = set_text
        self._Button = Button
        self.mouse = MouseController()
        self.kb = KeyController()

    def click(self, x, y):
        self.mouse.position = (x, y)
        time.sleep(0.05)
        self.mouse.click(self._Button.left)

    def input_text(self, text):
        if all(ord(c) < 128 for c in text):
            self.kb.type(text)
            return
        # 补充2:剪贴板可能被系统监听器瞬时占用,重试 3 次
        ok = False
        for _ in range(3):
            if self._set_text(text):
                ok = True
                break
            time.sleep(0.2)
        if not ok:
            raise RuntimeError("剪贴板写入失败(重试 3 次)")
        time.sleep(0.1)
        self.hotkey(["ctrl", "v"])

    def hotkey(self, keys):
        special = _special_map()
        ks = [special.get(k.lower(), k) for k in keys]
        for k in ks:
            self.kb.press(k)
        for k in reversed(ks):
            self.kb.release(k)


def main():
    ap = argparse.ArgumentParser(description="确定性回放脚本")
    ap.add_argument("script_path")
    ap.add_argument("--dry-run", action="store_true", help="只打印步骤不执行")
    a = ap.parse_args()

    set_dpi_aware()  # 补充1

    with open(a.script_path, "r", encoding="utf-8-sig") as f:
        script = json.load(f)
    errors = validate(script)
    if errors:
        alert("脚本不合法:\n" + "\n".join(errors))
        sys.exit(2)

    if a.dry_run:
        for i, s in enumerate(script["steps"]):
            print(i, json.dumps(s, ensure_ascii=False))
        return

    win = find_window(script["target"]["title_re"], enumerate_windows())
    if not win:
        alert("找不到目标窗口: %s\n请先打开目标程序。" % script["target"]["title_re"])
        sys.exit(2)

    log, failed = execute_script(script, win, RealExecutor())
    log_path = a.script_path + ".run_log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    if failed is not None:
        desc = script["steps"][failed].get("desc", "")
        alert("第 %d 步(%s %s)失败,已停止。日志: %s"
              % (failed, script["steps"][failed].get("action", ""), desc, log_path))
        sys.exit(1)
    print("回放完成,共 %d 步。日志: %s" % (len(log), log_path))


if __name__ == "__main__":
    main()
