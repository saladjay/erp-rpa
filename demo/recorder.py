# -*- coding: utf-8 -*-
"""最小录制器:3 秒倒数后开始,人工演示,F10 停止。
输出会话目录:events.jsonl + shot_xxx.png + intent.txt。"""
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.events import Event, write_event
from common.windowinfo import foreground_window_info, set_dpi_aware

from PIL import ImageGrab
from pynput import keyboard, mouse

CONSOLE_CLASSES = {"ConsoleWindowClass", "CASCADIA_HOSTING_WINDOW_CLASS", "mintty"}


class Recorder(object):
    def __init__(self, session_dir):
        self.session_dir = session_dir
        self.t0 = None
        self.index = 0
        self.stopped = False
        self.ml = None

    def _skip(self, win):
        return win is None or win.class_name in CONSOLE_CLASSES

    @staticmethod
    def normalize_key(k):
        """补充2:控制字符(ctrl+字母)映射为 'ctrl+字母';其余原样返回。"""
        if isinstance(k, str) and len(k) == 1 and ord(k) < 32:
            return "ctrl+" + chr(ord(k) + 96)
        return k

    def _record(self, ev):
        win = foreground_window_info()
        if self._skip(win):
            return
        ev.window = win.as_dict()
        shot = "shot_%03d.png" % self.index
        ImageGrab.grab().save(os.path.join(self.session_dir, shot))
        ev.screenshot = shot
        ev.index = self.index
        write_event(self.session_dir, ev)
        print("  [%02d] %s t=%.1fs" % (ev.index, ev.type, ev.t))
        self.index += 1

    def on_click(self, x, y, button, pressed):
        if self.stopped or pressed:      # 只记"抬起",一次点击一条
            return
        self._record(Event(index=self.index, t=time.time() - self.t0,
                           type="click", x=x, y=y, button=button.name))

    def on_press(self, key):
        if key == keyboard.Key.f10:
            self.stopped = True
            if self.ml:
                self.ml.stop()
            return False                 # 结束键盘监听
        if self.stopped:
            return
        if key == keyboard.Key.space:
            k = " "
        elif hasattr(key, "char") and key.char:
            k = key.char                 # pynput 已含 Shift 组合结果
        else:
            k = key.name                 # enter / ctrl / tab / ...
        k = self.normalize_key(k)        # 补充2
        self._record(Event(index=self.index, t=time.time() - self.t0,
                           type="key", key=k))

    def run(self):
        os.makedirs(self.session_dir, exist_ok=True)
        print("3 秒后开始录制:请切到目标窗口操作;按 F10 结束。")
        for i in range(3, 0, -1):
            print("  %d..." % i)
            time.sleep(1)
        self.t0 = time.time()
        print("录制中…")
        self.ml = mouse.Listener(on_click=self.on_click)
        kl = keyboard.Listener(on_press=self.on_press)
        self.ml.start()
        kl.start()
        kl.join()                        # 等 F10
        self.ml.join()
        intent = input("录制结束。请输入这段操作的意图说明(将发给大模型):\n> ")
        with open(os.path.join(self.session_dir, "intent.txt"), "w",
                  encoding="utf-8") as f:
            f.write(intent)
        print("会话已保存: %s(%d 个事件)" % (self.session_dir, self.index))


def main():
    set_dpi_aware()                      # 补充1:启动即 DPI 感知
    base = os.path.dirname(os.path.abspath(__file__))
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    Recorder(os.path.join(base, "sessions", stamp)).run()


if __name__ == "__main__":
    main()
