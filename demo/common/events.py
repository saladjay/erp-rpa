# -*- coding: utf-8 -*-
"""录制事件模型与会话文件读写(会话目录 = events.jsonl + 截图 + intent.txt)。"""
import json
import os
from dataclasses import asdict, dataclass
from typing import List, Optional

EVENTS_FILE = "events.jsonl"


@dataclass
class Event:
    index: int
    t: float                      # 距录制开始的秒数
    type: str                     # click / key
    x: Optional[int] = None
    y: Optional[int] = None
    button: Optional[str] = None
    key: Optional[str] = None     # 单键:字符或键名(enter/ctrl/...)
    text: Optional[str] = None    # merge_key_runs 合并出的连续文本
    window: Optional[dict] = None  # WindowInfo 的 dict 形式
    screenshot: Optional[str] = None


def events_path(session_dir):
    return os.path.join(session_dir, EVENTS_FILE)


def write_event(session_dir, event):
    with open(events_path(session_dir), "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")


def read_events(session_dir):
    out = []
    with open(events_path(session_dir), "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(Event(**json.loads(line)))
    return out


def _printable(k):
    return isinstance(k, str) and len(k) == 1


def merge_key_runs(events, gap_seconds=1.5):
    """把连续单字符按键合并成一条 text 事件;间隔超时、点击或其他键打断。"""
    out = []
    buf = []

    def flush():
        if buf:
            out.append(Event(index=buf[0].index, t=buf[0].t, type="key",
                             text="".join(e.key for e in buf),
                             window=buf[-1].window,
                             screenshot=buf[-1].screenshot))
            del buf[:]

    for ev in events:
        if ev.type == "key" and _printable(ev.key):
            if buf and (ev.t - buf[-1].t) > gap_seconds:
                flush()
            buf.append(ev)
        else:
            flush()
            out.append(ev)
    flush()
    for i, ev in enumerate(out):
        ev.index = i
    return out
