# -*- coding: utf-8 -*-
"""确定性回放引擎:零网络调用;失败即停(共识:运行时不问大模型)。"""
import re
import time


def find_window(title_re, windows):
    """windows = [(title, left, top)]。返回首个匹配项或 None。"""
    pat = re.compile(title_re)
    for title, left, top in windows:
        if pat.search(title):
            return title, left, top
    return None


def resolve_abs(win_left, win_top, locator):
    return win_left + locator["x"], win_top + locator["y"]


def execute_script(script, window, executor, sleep=time.sleep):
    """顺序执行;返回 (log, failed_index)。failed_index 为 None 表示全部成功。"""
    log = []
    for i, step in enumerate(script["steps"]):
        try:
            action = step["action"]
            if action == "click":
                x, y = resolve_abs(window[1], window[2], step["locator"])
                executor.click(x, y)
            elif action == "input":
                executor.input_text(step["text"])
            elif action == "hotkey":
                executor.hotkey(step["keys"])
            elif action == "wait":
                sleep(step["seconds"])
            log.append({"step": i, "action": action, "ok": True})
        except Exception as exc:
            log.append({"step": i, "action": step.get("action"),
                        "ok": False, "error": str(exc)})
            return log, i
    return log, None


def enumerate_windows():
    """[(title, left, top)] 真实窗口枚举(pywinauto win32 后端,Win7 兼容)。"""
    from pywinauto import Desktop
    out = []
    for w in Desktop(backend="win32").windows():
        try:
            r = w.rectangle()
            out.append((w.window_text(), r.left, r.top))
        except Exception:
            continue
    return out
