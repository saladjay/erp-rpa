# -*- coding: utf-8 -*-
"""最小录制器:3 秒倒数后开始,人工演示,F10 停止。
输出会话目录:events.jsonl + shot_xxx.png + intent.txt。
回调线程只抓屏入队;PNG 编码/写盘在单独写线程,避免 WH_MOUSE_LL 钩子超时。"""
import datetime
import os
import queue
import sys
import threading
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
        self.q = queue.Queue()
        self.writer_error = None

    def _skip(self, win):
        return win is None or win.class_name in CONSOLE_CLASSES

    @staticmethod
    def normalize_key(k):
        """补充2:0x01-0x1A(ctrl+字母)映射为 'ctrl+字母';
        其余控制字符(0x00、0x1B-0x1F、0x7F)返回占位,不进时间线。"""
        if isinstance(k, str) and len(k) == 1:
            code = ord(k)
            if 0x01 <= code <= 0x1A:
                return "ctrl+" + chr(code + 96)
            if code < 0x20 or code == 0x7F:
                return "ctrl+?_unmapped"
        return k

    def _writer(self):
        """单写线程:PNG 编码、写盘、jsonl、index 递增全在这里;
        异常记入 self.writer_error 后退出,不让写线程无声死。"""
        while True:
            item = self.q.get()
            if item is None:
                return
            ev, img = item
            try:
                shot = "shot_%03d.png" % self.index
                img.save(os.path.join(self.session_dir, shot))
                ev.screenshot = shot
                ev.index = self.index
                write_event(self.session_dir, ev)
                print("  [%02d] %s t=%.1fs" % (ev.index, ev.type, ev.t))
                self.index += 1
            except Exception as e:
                self.writer_error = e
                return

    def _record(self, ev):
        win = foreground_window_info()
        if self._skip(win):
            return
        ev.window = win.as_dict()
        img = ImageGrab.grab()           # 只截图,不编码
        self.q.put((ev, img))            # 重活全部交给写线程,立即返回

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
            # 无 name 的 KeyCode(如部分 IME 按键)不崩监听器,记 vk 占位
            k = getattr(key, "name", None) or ("vk_%s" % getattr(key, "vk", "?"))
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
        self.writer = threading.Thread(target=self._writer, daemon=True)
        self.writer.start()              # 先起写线程,再开监听
        self.ml = mouse.Listener(on_click=self.on_click)
        kl = keyboard.Listener(on_press=self.on_press)
        self.ml.start()
        kl.start()
        try:
            kl.join()                    # 等 F10;回调抛的异常会在这里重抛
            self.ml.join()
        except Exception as e:
            print("监听器异常(已尽量保存事件): %s" % e)
        finally:
            self.q.put(None)             # 无论成败都收尾写线程
            self.writer.join()
        # intent 无论如何都要写:缺 intent 整个会话作废
        intent = input("录制结束。请输入这段操作的意图说明(将发给大模型):\n> ")
        with open(os.path.join(self.session_dir, "intent.txt"), "w",
                  encoding="utf-8") as f:
            f.write(intent)
        if self.writer_error is not None:
            print("警告:部分事件可能丢失: %s" % self.writer_error)
        print("会话已保存: %s(%d 个事件)" % (self.session_dir, self.index))


def main():
    set_dpi_aware()                      # 补充1:启动即 DPI 感知
    base = os.path.dirname(os.path.abspath(__file__))
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    Recorder(os.path.join(base, "sessions", stamp)).run()


if __name__ == "__main__":
    main()
