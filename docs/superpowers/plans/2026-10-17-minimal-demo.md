# 最小演示 Demo 实施计划(录制 → VLM 编译 → 确定性回放)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在开发机(Win11)上以记事本代替 ERP,跑通"人工演示录制 → GLM-4.1V 编译脚本 → 零大模型确定性回放"完整链路的最小 demo。

**Architecture:** 三个 CLI 组件 + 一个公共库:`recorder.py`(pynput 监听键鼠,每事件存截图+窗口信息到会话目录)→ `compiler.py`(把事件时间线+截图+意图喂给 OpenAI 兼容 VLM,产出人可读 JSON 脚本,代码侧做坐标换算与校验)→ `player.py`(纯本地执行脚本:窗口相对坐标定位,失败即停并 MessageBox 报警,全程零网络调用)。

**Tech Stack:** Python 3.8.10(**32 位**,Win7 同款运行时)、pynput 1.7.7、Pillow 10.4.0、pywinauto 0.6.8、requests 2.32.3、pytest 8.3.5、vermin 1.6.0。

**Win7 兼容纪律(全任务生效):** 所有代码必须 Python 3.8 语法(不用 3.9+ 特性:`match`、`dict |`、内建泛型注解等);Windows API 只经 ctypes/pynput/pywinauto/PIL 老接口;每个任务收尾跑 vermin 检查。

**不在本 demo 范围(后续任务):** UIA/图像定位策略、脚本参数化与数据驱动(字段映射/循环)、定时触发、业务人员 GUI、ERP 真机适配。demo 只有 `offset`(窗口相对坐标)定位。

---

### Task 1: 仓库初始化 + Python 3.8-32 环境 + 依赖锁 + 离线轮子仓

**Files:**
- Create: `.gitignore`
- Create: `demo/requirements.txt`
- Create: `demo/common/__init__.py`(空文件)
- Create: `demo/tests/conftest.py`

- [ ] **Step 1: 初始化 git 仓库**

```bash
cd /d/project/AI-RPA-ERP
git init
```

Expected: `Initialized empty Git repository`

- [ ] **Step 2: 写 .gitignore**

```gitignore
__pycache__/
*.pyc
.venv*/
demo/config.json
demo/sessions/
probe/probe_report_*/
wheels/
```

- [ ] **Step 3: 写依赖清单(全部 pin,均有 win32/3.8 轮子)**

`demo/requirements.txt`:
```
pynput==1.7.7
Pillow==10.4.0
pywinauto==0.6.8
comtypes==1.4.6
requests==2.32.3
pytest==8.3.5
vermin==1.6.0
```

- [ ] **Step 4: 写测试路径配置**

`demo/tests/conftest.py`:
```python
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **Step 5: 安装 32 位 Python 3.8.10 并建 venv(人工前置:若未装)**

从 https://www.python.org/downloads/release/python-3810/ 下载 **Windows x86 executable installer** 安装(与现有 64 位 Python 并存,不影响)。然后:

```bash
py -3.8-32 -m venv .venv38
.venv38/Scripts/python -c "import struct,sys;print(sys.version, struct.calcsize('P')*8)"
```

Expected: 输出 `3.8.10 ... 32`(32 位确认)

- [ ] **Step 6: 装依赖 + 下载 win32 离线轮子仓**

```bash
.venv38/Scripts/python -m pip install --upgrade pip==24.3.1
.venv38/Scripts/python -m pip install -r demo/requirements.txt
.venv38/Scripts/python -m pip download -r demo/requirements.txt -d wheels
```

Expected: 全部安装成功;`wheels/` 下出现各包的 `win32` 或纯 Python 轮子文件。

- [ ] **Step 7: 提交**

```bash
git add .gitignore demo/
git commit -m "chore: init repo, pin py3.8-32 deps, offline wheels"
```

---

### Task 2: 配置模块 common/config.py

**Files:**
- Create: `demo/common/config.py`
- Test: `demo/tests/test_config.py`

- [ ] **Step 1: 写失败测试**

`demo/tests/test_config.py`:
```python
import json

import pytest

from common.config import load_config


def test_load_config_reads_json(tmp_path):
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(json.dumps({"vlm": {"api_key": "k"}}), encoding="utf-8")
    assert load_config(str(tmp_path)) == {"vlm": {"api_key": "k"}}


def test_load_config_copies_example_then_raises(tmp_path):
    (tmp_path / "config.example.json").write_text(
        json.dumps({"vlm": {"api_key": "填我"}}), encoding="utf-8")
    with pytest.raises(RuntimeError) as ei:
        load_config(str(tmp_path))
    assert "api_key" in str(ei.value)
    assert (tmp_path / "config.json").exists()


def test_load_config_missing_all(tmp_path):
    with pytest.raises(RuntimeError):
        load_config(str(tmp_path))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_config.py -v`
Expected: FAIL(`ModuleNotFoundError: common.config`)

- [ ] **Step 3: 实现**

`demo/common/config.py`:
```python
# -*- coding: utf-8 -*-
"""配置加载:首次运行从 config.example.json 复制并提示填 key。"""
import json
import os
import shutil


def load_config(base_dir):
    path = os.path.join(base_dir, "config.json")
    example = os.path.join(base_dir, "config.example.json")
    if not os.path.exists(path):
        if os.path.exists(example):
            shutil.copyfile(example, path)
            raise RuntimeError(
                "已生成 %s,请填入 api_key 后重试" % path)
        raise RuntimeError("缺少配置文件: %s" % path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: 提交**

```bash
git add demo/common/config.py demo/tests/test_config.py
git commit -m "feat: config loader with example bootstrap"
```

---

### Task 3: 事件模型与会话读写 common/events.py

**Files:**
- Create: `demo/common/events.py`
- Test: `demo/tests/test_events.py`

- [ ] **Step 1: 写失败测试**

`demo/tests/test_events.py`:
```python
from common.events import Event, write_event, read_events, merge_key_runs


def test_jsonl_roundtrip(tmp_path):
    write_event(str(tmp_path),
                Event(index=0, t=0.1, type="click", x=1, y=2, button="left"))
    write_event(str(tmp_path), Event(index=1, t=0.5, type="key", key="a"))
    evs = read_events(str(tmp_path))
    assert len(evs) == 2
    assert evs[0].type == "click" and evs[0].x == 1
    assert evs[1].key == "a"


def _key(i, t, ch):
    return Event(index=i, t=t, type="key", key=ch)


def test_merge_text_run():
    evs = [_key(0, 0.0, "h"), _key(1, 0.2, "i"),
           Event(index=2, t=0.4, type="key", key="enter")]
    out = merge_key_runs(evs)
    assert out[0].text == "hi" and out[0].type == "key"
    assert out[1].key == "enter"


def test_merge_includes_spaces():
    evs = [_key(0, 0.0, "h"), _key(1, 0.1, " "), _key(2, 0.2, "i")]
    out = merge_key_runs(evs)
    assert out[0].text == "h i"


def test_merge_breaks_on_gap():
    evs = [_key(0, 0.0, "a"), _key(1, 3.0, "b")]
    out = merge_key_runs(evs)
    assert [e.text for e in out] == ["a", "b"]


def test_merge_keeps_clicks_between():
    evs = [_key(0, 0.0, "a"),
           Event(index=1, t=0.1, type="click", x=5, y=5),
           _key(2, 0.2, "b")]
    out = merge_key_runs(evs)
    assert len(out) == 3
    assert out[0].text == "a" and out[1].type == "click" and out[2].text == "b"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_events.py -v`
Expected: FAIL(`No module named 'common.events'`)

- [ ] **Step 3: 实现**

`demo/common/events.py`:
```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_events.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add demo/common/events.py demo/tests/test_events.py
git commit -m "feat: recording event model, jsonl io, key-run merge"
```

---

### Task 4: 前台窗口信息抓取 common/windowinfo.py

**Files:**
- Create: `demo/common/windowinfo.py`
- Test: `demo/tests/test_windowinfo.py`

- [ ] **Step 1: 写失败测试**

`demo/tests/test_windowinfo.py`:
```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_windowinfo.py -v`
Expected: FAIL(import 错误)

- [ ] **Step 3: 实现**

`demo/common/windowinfo.py`:
```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_windowinfo.py -v`
Expected: 1 passed

- [ ] **Step 5: 提交**

```bash
git add demo/common/windowinfo.py demo/tests/test_windowinfo.py
git commit -m "feat: foreground window info via ctypes"
```

---

### Task 5: 脚本契约与校验 common/script.py

**Files:**
- Create: `demo/common/script.py`
- Test: `demo/tests/test_script.py`

- [ ] **Step 1: 写失败测试**

`demo/tests/test_script.py`:
```python
from common.script import validate

VALID = {
    "name": "notepad-demo",
    "target": {"title_re": "记事本|Notepad"},
    "steps": [
        {"action": "click", "locator": {"strategy": "offset", "x": 100, "y": 60},
         "desc": "点编辑区"},
        {"action": "input", "text": "你好", "desc": "输入"},
        {"action": "hotkey", "keys": ["ctrl", "s"], "desc": "保存"},
        {"action": "wait", "seconds": 0.5, "desc": "等"},
    ],
}


def test_valid_script():
    assert validate(VALID) == []


def test_not_dict():
    assert validate([1, 2]) == ["脚本必须是 JSON 对象"]


def test_missing_name_and_target():
    errs = validate({"steps": VALID["steps"]})
    assert any("name" in e for e in errs)
    assert any("title_re" in e for e in errs)


def test_empty_steps():
    errs = validate(dict(VALID, steps=[]))
    assert any("steps" in e for e in errs)


def test_unknown_action():
    bad = dict(VALID, steps=[{"action": "scroll", "locator": {}}])
    assert any("action" in e for e in validate(bad))


def test_click_needs_int_locator():
    bad = dict(VALID, steps=[{"action": "click",
                              "locator": {"strategy": "offset", "x": "a", "y": 1}}])
    errs = validate(bad)
    assert any("x" in e for e in errs)


def test_input_needs_text():
    bad = dict(VALID, steps=[{"action": "input"}])
    assert any("text" in e for e in validate(bad))


def test_hotkey_needs_keys():
    bad = dict(VALID, steps=[{"action": "hotkey", "keys": []}])
    assert any("keys" in e for e in validate(bad))


def test_wait_needs_positive_seconds():
    bad = dict(VALID, steps=[{"action": "wait", "seconds": 0}])
    assert any("seconds" in e for e in validate(bad))
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_script.py -v`
Expected: FAIL(import 错误)

- [ ] **Step 3: 实现**

`demo/common/script.py`:
```python
# -*- coding: utf-8 -*-
"""回放脚本契约与校验。脚本是人可读可手改的 JSON(共识:小改手改脚本)。"""
ALLOWED_ACTIONS = ("click", "input", "hotkey", "wait")
ALLOWED_STRATEGIES = ("offset",)  # demo 仅 offset;后续加 uia / image


def validate(script):
    errors = []
    if not isinstance(script, dict):
        return ["脚本必须是 JSON 对象"]
    if not isinstance(script.get("name"), str) or not script.get("name"):
        errors.append("缺少非空 name")
    target = script.get("target")
    if not isinstance(target, dict) or not target.get("title_re"):
        errors.append("缺少 target.title_re")
    steps = script.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps 必须是非空数组")
        return errors
    for i, step in enumerate(steps):
        p = "steps[%d]" % i
        if not isinstance(step, dict):
            errors.append(p + " 必须是对象")
            continue
        action = step.get("action")
        if action not in ALLOWED_ACTIONS:
            errors.append("%s action=%r 不合法(允许 %s)" % (p, action, ALLOWED_ACTIONS))
            continue
        if action == "click":
            loc = step.get("locator")
            if not isinstance(loc, dict):
                errors.append(p + " click 需要 locator")
                continue
            if loc.get("strategy") not in ALLOWED_STRATEGIES:
                errors.append(p + " locator.strategy 只支持 " + str(ALLOWED_STRATEGIES))
            for f in ("x", "y"):
                if not isinstance(loc.get(f), int):
                    errors.append("%s locator.%s 必须是整数" % (p, f))
        elif action == "input":
            if not isinstance(step.get("text"), str):
                errors.append(p + " input 需要 text 字符串")
        elif action == "hotkey":
            keys = step.get("keys")
            if (not isinstance(keys, list) or not keys
                    or not all(isinstance(k, str) for k in keys)):
                errors.append(p + " hotkey 需要 keys 非空字符串数组")
        elif action == "wait":
            if not isinstance(step.get("seconds"), (int, float)) or step["seconds"] <= 0:
                errors.append(p + " wait 需要 seconds 正数")
    return errors
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_script.py -v`
Expected: 9 passed

- [ ] **Step 5: 提交**

```bash
git add demo/common/script.py demo/tests/test_script.py
git commit -m "feat: replay script contract and validator"
```

---

### Task 6: 剪贴板助手 common/clipboard.py(输入中文用)

**Files:**
- Create: `demo/common/clipboard.py`
- Test: `demo/tests/test_clipboard.py`

- [ ] **Step 1: 写失败测试**

`demo/tests/test_clipboard.py`:
```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_clipboard.py -v`
Expected: FAIL(import 错误)

- [ ] **Step 3: 实现**

`demo/common/clipboard.py`:
```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_clipboard.py -v`
Expected: 1 passed

- [ ] **Step 5: 提交**

```bash
git add demo/common/clipboard.py demo/tests/test_clipboard.py
git commit -m "feat: clipboard helper for non-ascii input"
```

---

### Task 7: VLM 客户端 common/vlmclient.py(OpenAI 兼容,requests 直连)

**Files:**
- Create: `demo/common/vlmclient.py`
- Test: `demo/tests/test_vlmclient.py`

- [ ] **Step 1: 写失败测试**

`demo/tests/test_vlmclient.py`:
```python
import pytest

from common.vlmclient import VLMClient, VLMError, extract_json


def test_extract_json_from_fence():
    text = "脚本如下:\n```json\n{\"name\": \"d\", \"steps\": []}\n```"
    assert extract_json(text) == {"name": "d", "steps": []}


def test_extract_json_bare():
    assert extract_json("前缀 {\"a\": 1} 后缀") == {"a": 1}


def test_extract_json_invalid():
    with pytest.raises(ValueError):
        extract_json("没有 JSON")


class _Resp(object):
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def test_chat_parses_content(monkeypatch):
    import common.vlmclient as v

    def fake_post(url, headers=None, json=None, timeout=None):
        assert url.endswith("/chat/completions")
        assert headers["Authorization"] == "Bearer k"
        return _Resp({"choices": [{"message": {"content": "{\"ok\": 1}"}}]})

    monkeypatch.setattr(v.requests, "post", fake_post)
    c = v.VLMClient({"base_url": "https://x/api/paas/v4", "api_key": "k",
                     "model": "m", "timeout_seconds": 5})
    assert c.chat([{"role": "user", "content": "hi"}]) == "{\"ok\": 1}"


def test_chat_empty_content_raises(monkeypatch):
    import common.vlmclient as v

    monkeypatch.setattr(v.requests, "post", lambda *a, **kw: _Resp(
        {"choices": [{"message": {"content": None}}]}))
    c = v.VLMClient({"base_url": "https://x", "api_key": "k",
                     "model": "m", "timeout_seconds": 5})
    with pytest.raises(VLMError):
        c.chat([{"role": "user", "content": "hi"}])
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_vlmclient.py -v`
Expected: FAIL(import 错误)

- [ ] **Step 3: 实现**

`demo/common/vlmclient.py`:
```python
# -*- coding: utf-8 -*-
"""OpenAI 兼容 Chat API 客户端(requests 直连,不依赖 SDK;
Python 自带 OpenSSL,Win7 无 TLS 问题)。"""
import base64
import io
import json
import re

import requests


class VLMError(RuntimeError):
    pass


class VLMClient(object):
    def __init__(self, cfg):
        self.base_url = cfg["base_url"].rstrip("/")
        self.api_key = cfg["api_key"]
        self.model = cfg["model"]
        self.timeout = cfg.get("timeout_seconds", 120)

    def chat(self, messages):
        url = self.base_url + "/chat/completions"
        headers = {"Authorization": "Bearer " + self.api_key}
        payload = {"model": self.model, "messages": messages}
        r = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            content = None
        if not content:
            raise VLMError("VLM 空回复:" + json.dumps(data, ensure_ascii=False)[:500])
        return content


def extract_json(text):
    """从模型回复中剥掉 ```json 围栏/前后闲话,解析出 JSON 对象。"""
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.S)
    if m:
        text = m.group(1)
    else:
        s, e = text.find("{"), text.rfind("}")
        if s >= 0 and e > s:
            text = text[s:e + 1]
    return json.loads(text)


def image_data_url(path, max_width=1280):
    """截图缩放后转 data URL 喂给视觉模型。"""
    from PIL import Image
    img = Image.open(path)
    if img.width > max_width:
        ratio = max_width / float(img.width)
        img = img.resize((max_width, int(img.height * ratio)))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_vlmclient.py -v`
Expected: 5 passed

- [ ] **Step 5: 提交**

```bash
git add demo/common/vlmclient.py demo/tests/test_vlmclient.py
git commit -m "feat: openai-compatible vlm client with fence-stripping"
```

---

### Task 8: 编译器 compiler.py(会话 → 脚本)

**Files:**
- Create: `demo/common/compiler.py`
- Create: `demo/compiler.py`
- Test: `demo/tests/test_compiler.py`

- [ ] **Step 1: 写失败测试**

`demo/tests/test_compiler.py`:
```python
import json
import os

from PIL import Image

from common.compiler import event_lines, compile_session, SYSTEM_PROMPT
from common.events import Event, write_event

VALID_SCRIPT = {
    "name": "notepad-demo",
    "target": {"title_re": "记事本|Notepad"},
    "steps": [
        {"action": "click", "locator": {"strategy": "offset", "x": 200, "y": 150}},
        {"action": "input", "text": "你好"},
    ],
}


class FakeClient(object):
    def __init__(self, script):
        self.script = script
        self.messages = None

    def chat(self, messages):
        self.messages = messages
        return "```json\n" + json.dumps(self.script, ensure_ascii=False) + "\n```"


def test_event_lines_click_contains_win_rel():
    ev = Event(index=3, t=2.5, type="click", x=300, y=200, button="left",
               window={"left": 100, "top": 50, "title": "记事本"})
    assert "win_rel=(200,150)" in event_lines([ev])[0]


def test_event_lines_text_run():
    ev = Event(index=0, t=1.0, type="key", text="你好")
    assert "你好" in event_lines([ev])[0]


def _make_session(tmp_path):
    d = str(tmp_path)
    write_event(d, Event(index=0, t=0.5, type="click", x=300, y=200,
                         button="left", screenshot="shot_000.png",
                         window={"left": 100, "top": 50, "title": "记事本"}))
    write_event(d, Event(index=1, t=1.5, type="key", text="你好"))
    with open(os.path.join(d, "intent.txt"), "w", encoding="utf-8") as f:
        f.write("在记事本里输入问候语")
    Image.new("RGB", (10, 10), "white").save(os.path.join(d, "shot_000.png"))
    return d


def test_compile_session_writes_script(tmp_path):
    d = _make_session(tmp_path)
    fake = FakeClient(VALID_SCRIPT)
    out = compile_session(d, fake)
    assert out.endswith("script.json")
    with open(out, encoding="utf-8") as f:
        assert json.load(f)["steps"]
    assert fake.messages[0]["role"] == "system"
    assert "记事本" in fake.messages[1]["content"][0]["text"]
    # 至少一张图以 image_url 形式进入消息
    kinds = [c["type"] for c in fake.messages[1]["content"]]
    assert "image_url" in kinds
    assert os.path.exists(os.path.join(d, "vlm_response.txt"))


def test_compile_session_invalid_script_raises(tmp_path):
    d = _make_session(tmp_path)
    bad = dict(VALID_SCRIPT, steps=[{"action": "不存在"}])
    import pytest
    with pytest.raises(ValueError):
        compile_session(d, FakeClient(bad))


def test_system_prompt_states_schema():
    assert "title_re" in SYSTEM_PROMPT and "win_rel" in SYSTEM_PROMPT
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_compiler.py -v`
Expected: FAIL(import 错误)

- [ ] **Step 3: 实现 common/compiler.py**

`demo/common/compiler.py`:
```python
# -*- coding: utf-8 -*-
"""会话 → 确定性脚本 编译器。大模型只在这里出现(共识:LLM 仅创作期)。"""
import json
import os

from common.events import merge_key_runs, read_events
from common.script import validate
from common.vlmclient import extract_json, image_data_url

MAX_IMAGES = 20

SYSTEM_PROMPT = """你是 Windows 桌面自动化脚本编译器。输入是一次人工演示的事件时间线(每步附截图)和操作意图,请把它编译成确定性的回放脚本。
只输出严格 JSON,不要任何解释文字,结构:
{
  "name": "脚本名(英文或拼音)",
  "target": {"title_re": "匹配目标窗口标题的正则"},
  "steps": [
    {"action": "click", "locator": {"strategy": "offset", "x": <int>, "y": <int>}, "desc": "中文说明"},
    {"action": "input", "text": "<要输入的文本>", "desc": "中文说明"},
    {"action": "hotkey", "keys": ["ctrl", "s"], "desc": "中文说明"},
    {"action": "wait", "seconds": 0.5, "desc": "中文说明"}
  ]
}
规则:
1. 点击坐标一律使用时间线里给出的 win_rel(窗口相对坐标),禁止自己换算绝对坐标。
2. 合并:连续输入文本是一条 input;一次点击是一条 click;组合键(如保存)是 hotkey。
3. 打开/切换窗口、保存等操作后,插入 wait(0.5~1 秒)。
4. 省略演示中的犹豫、误点(点了又马上点别处的孤立点击);只保留达成意图所必需的步骤。
5. target.title_re 用宽松正则匹配窗口标题(标题可能带文件名,如 "xxx - 记事本")。"""


def event_lines(events):
    lines = []
    for ev in events:
        if ev.type == "click":
            w = ev.window or {}
            if w and ev.x is not None:
                rx, ry = ev.x - w.get("left", 0), ev.y - w.get("top", 0)
                rel = "win_rel=(%d,%d)" % (rx, ry)
            else:
                rel = "win_rel=?"
            lines.append("[%d] t=%.1fs %s键点击 abs=(%s,%s) %s 窗口="%s""
                         % (ev.index, ev.t, ev.button or "左", ev.x, ev.y, rel,
                            (w.get("title") or "")[:30]))
        elif ev.type == "key":
            if ev.text is not None:
                lines.append("[%d] t=%.1fs 输入文本 %r" % (ev.index, ev.t, ev.text))
            else:
                lines.append("[%d] t=%.1fs 按键 %s" % (ev.index, ev.t, ev.key))
    return lines


def compile_session(session_dir, client, out_path=None):
    events = merge_key_runs(read_events(session_dir))
    intent_path = os.path.join(session_dir, "intent.txt")
    with open(intent_path, "r", encoding="utf-8") as f:
        intent = f.read().strip()
    if not intent:
        raise ValueError("intent.txt 为空,请说明操作意图")

    shots = [ev.screenshot for ev in events if ev.screenshot][:MAX_IMAGES]
    text_part = ("操作意图:%s\n\n事件时间线:\n%s\n\n请输出脚本 JSON。"
                 % (intent, "\n".join(event_lines(events))))
    content = [{"type": "text", "text": text_part}]
    for s in shots:
        p = os.path.join(session_dir, s)
        if os.path.exists(p):
            content.append({"type": "image_url",
                            "image_url": {"url": image_data_url(p)}})

    messages = [{"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content}]
    raw = client.chat(messages)
    with open(os.path.join(session_dir, "vlm_response.txt"), "w", encoding="utf-8") as f:
        f.write(raw)

    script = extract_json(raw)
    errors = validate(script)
    if errors:
        raise ValueError("VLM 产出的脚本不合法:\n" + "\n".join(errors))
    out = out_path or os.path.join(session_dir, "script.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)
    return out
```

- [ ] **Step 4: 实现 CLI 入口**

`demo/compiler.py`:
```python
# -*- coding: utf-8 -*-
"""用法: python compiler.py sessions/20260101_120000"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.compiler import compile_session
from common.config import load_config
from common.vlmclient import VLMClient


def main():
    ap = argparse.ArgumentParser(description="把录制会话编译成回放脚本")
    ap.add_argument("session_dir")
    a = ap.parse_args()
    base = os.path.dirname(os.path.abspath(__file__))
    cfg = load_config(base)
    client = VLMClient(cfg["vlm"])
    out = compile_session(a.session_dir, client)
    print("脚本已生成: %s(请人工审阅后再回放)" % out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: 跑测试确认通过**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_compiler.py -v`
Expected: 5 passed

- [ ] **Step 6: 提交**

```bash
git add demo/common/compiler.py demo/compiler.py demo/tests/test_compiler.py
git commit -m "feat: session compiler with vlm prompt and validation gate"
```

---

### Task 9: 回放器 player.py(零模型、失败即停+报警)

**Files:**
- Create: `demo/common/player.py`
- Create: `demo/player.py`
- Test: `demo/tests/test_player.py`

- [ ] **Step 1: 写失败测试**

`demo/tests/test_player.py`:
```python
from common.player import execute_script, find_window, resolve_abs

SCRIPT = {
    "name": "t",
    "target": {"title_re": "x"},
    "steps": [
        {"action": "click", "locator": {"strategy": "offset", "x": 1, "y": 2}},
        {"action": "wait", "seconds": 0.3},
        {"action": "input", "text": "你好"},
    ],
}


def test_find_window_regex():
    wins = [("无标题 - 记事本", 10, 20), ("Chrome", 0, 0)]
    assert find_window("记事本|Notepad", wins) == ("无标题 - 记事本", 10, 20)
    assert find_window("不存在的", wins) is None


def test_resolve_abs():
    assert resolve_abs(100, 200, {"x": 5, "y": 10}) == (105, 210)


class FakeExecutor(object):
    def __init__(self):
        self.calls = []

    def click(self, x, y):
        self.calls.append(("click", x, y))

    def input_text(self, text):
        self.calls.append(("input", text))

    def hotkey(self, keys):
        self.calls.append(("hotkey", tuple(keys)))


def test_execute_script_order_and_wait():
    slept = []
    ex = FakeExecutor()
    log, failed = execute_script(SCRIPT, ("t", 10, 20), ex,
                                 sleep=lambda s: slept.append(s))
    assert failed is None
    assert ex.calls[0] == ("click", 11, 22)
    assert ex.calls[1] == ("input", "你好")
    assert slept == [0.3]
    assert all(e["ok"] for e in log)


def test_execute_script_stops_on_error():
    class Boom(FakeExecutor):
        def input_text(self, text):
            raise RuntimeError("输入失败")

    log, failed = execute_script(SCRIPT, ("t", 0, 0), Boom())
    assert failed == 2
    assert log[-1]["ok"] is False and "输入失败" in log[-1]["error"]
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_player.py -v`
Expected: FAIL(import 错误)

- [ ] **Step 3: 实现 common/player.py**

`demo/common/player.py`:
```python
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
```

- [ ] **Step 4: 实现 CLI 入口**

`demo/player.py`:
```python
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
        if not self._set_text(text):
            raise RuntimeError("剪贴板写入失败")
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

    with open(a.script_path, "r", encoding="utf-8") as f:
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
```

- [ ] **Step 5: 跑测试确认通过**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_player.py -v`
Expected: 4 passed

- [ ] **Step 6: 提交**

```bash
git add demo/common/player.py demo/player.py demo/tests/test_player.py
git commit -m "feat: deterministic replay engine, stop-and-alert semantics"
```

---

### Task 10: 录制器 recorder.py

**Files:**
- Create: `demo/recorder.py`
- Test: `demo/tests/test_recorder.py`(只测纯逻辑;监听链路走 Task 11 人工验证)

- [ ] **Step 1: 写失败测试**

`demo/tests/test_recorder.py`:
```python
from common.windowinfo import WindowInfo
from recorder import Recorder


def _win(cls):
    return WindowInfo(title="t", class_name=cls, left=0, top=0, right=1, bottom=1)


def test_skip_console_windows():
    r = Recorder.__new__(Recorder)          # 不跑 __init__,只测纯逻辑
    assert r._skip(_win("ConsoleWindowClass")) is True
    assert r._skip(_win("CASCADIA_HOSTING_WINDOW_CLASS")) is True
    assert r._skip(_win("Notepad")) is False
    assert r._skip(None) is True
```

- [ ] **Step 2: 跑测试确认失败**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_recorder.py -v`
Expected: FAIL(`No module named 'recorder'`)

- [ ] **Step 3: 实现**

`demo/recorder.py`:
```python
# -*- coding: utf-8 -*-
"""最小录制器:3 秒倒数后开始,人工演示,F10 停止。
输出会话目录:events.jsonl + shot_xxx.png + intent.txt。"""
import datetime
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.events import Event, write_event
from common.windowinfo import foreground_window_info

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
    base = os.path.dirname(os.path.abspath(__file__))
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    Recorder(os.path.join(base, "sessions", stamp)).run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑测试确认通过**

Run: `.venv38/Scripts/python -m pytest demo/tests/test_recorder.py -v`
Expected: 1 passed

- [ ] **Step 5: 提交**

```bash
git add demo/recorder.py demo/tests/test_recorder.py
git commit -m "feat: minimal recorder with per-event screenshots and intent"
```

---

### Task 11: 全量测试 + vermin 门禁 + 端到端演示(Win11 记事本)

**Files:**
- Create: `demo/config.example.json`
- Create: `docs/demo-checklist.md`

- [ ] **Step 1: 写配置样例**

`demo/config.example.json`:
```json
{
  "vlm": {
    "base_url": "https://open.bigmodel.cn/api/paas/v4",
    "api_key": "在 https://bigmodel.cn 注册后填入",
    "model": "glm-4.1v-thinking-flash",
    "timeout_seconds": 180
  }
}
```

- [ ] **Step 2: 全量测试 + 最低版本门禁**

```bash
.venv38/Scripts/python -m pytest demo/tests -v
.venv38/Scripts/python -m vermin -t=3.8- demo/common demo/recorder.py demo/compiler.py demo/player.py
```

Expected: 全部 passed;vermin 输出 `Minimum required versions: 3.8`(若报更高,修掉 3.9+ 语法再继续)。

- [ ] **Step 3: 人工端到端演示(开发机,记事本代替 ERP)**

前置:到 https://bigmodel.cn 注册拿 API Key(免费档),填入 `demo/config.json`(首次运行 compiler 会自动从 example 复制)。

1. 打开记事本(新建空文档);
2. `cd demo && ../.venv38/Scripts/python recorder.py` → 3 秒倒数内点进记事本 → 在编辑区点一下 → 输入 `你好,世界 Hello 123` → F10 → 意图输入"在记事本编辑区输入一段问候语";
3. `../.venv38/Scripts/python compiler.py sessions/<刚生成的目录>` → 打开 `script.json` 人工审阅(两道闸之一);
4. 清空记事本内容(全选删除),回放:`../.venv38/Scripts/python player.py sessions/<目录>/script.json` → 观察文本被确定性重现;
5. 失败路径验证:关闭记事本再回放 → 应弹"找不到目标窗口"报警并退出码 2。

- [ ] **Step 4: 记录演示结果**

`docs/demo-checklist.md`:
```markdown
# 最小 Demo 演示记录

- 日期 / 机器:
- 录制会话目录:
- 编译产物 script.json 摘要(步骤数 / 各步 desc):
- 回放结果:成功/失败,run_log.json 路径
- 失败路径验证:报警截图或描述
- VLM 响应原文存档: sessions/<dir>/vlm_response.txt
- 已知问题与改进项:
```

填完后提交:
```bash
git add demo/config.example.json docs/demo-checklist.md demo/sessions
git commit -m "docs: e2e demo record on win11 notepad"
```
(若 .gitignore 已排除 sessions/,改为只提交 checklist。)

---

### Task 12: Win7 移植防线(部署包 + 冒烟清单)

**Files:**
- Create: `install.bat`
- Create: `docs/win7-smoke.md`

- [ ] **Step 1: 写离线安装脚本**

`install.bat`(放仓库根,目标 Win7 机器执行):
```bat
@echo off
rem 前置:目标机已装 32 位 Python 3.8.10(含 py 启动器)
rem 本目录需包含 demo\ 与 wheels\
py -3.8-32 -m pip install --no-index --find-links wheels -r demo\requirements.txt
if errorlevel 1 (echo 依赖安装失败 & exit /b 1)
echo 依赖安装完成。执行演示见 docs\win7-smoke.md
```

- [ ] **Step 2: 写 Win7 冒烟清单**

`docs/win7-smoke.md`:
```markdown
# Win7 32 位冒烟清单(每阶段交付前执行)

环境:32 位 Win7(SP1),已装 Python 3.8.10 x86。
材料:整个仓库目录(含 wheels/)拷到目标机。

1. `install.bat` → 依赖离线安装成功
2. `py -3.8-32 -m pytest demo\tests -v` → 全绿(不需要网络/大模型)
3. 记事本端到端:recorder → compiler(需联网+API Key)→ player,同 demo-checklist
4. 断网验证:仅跑 player(回放零网络,共识红线)
5. 记录:系统版本(winver)、DPI、通过/失败项
```

- [ ] **Step 3: 若有 Win7 虚拟机/真机,现在执行一遍冒烟并记录;没有则标注"待执行"后提交**

```bash
git add install.bat docs/win7-smoke.md
git commit -m "build: win7 offline install + smoke checklist"
```

---

## 自查记录(写计划后核对)

- **覆盖**:共识链路三组件+意图+人工审阅闸+失败报警+人可改 JSON 脚本+Win7 五道防线(同运行时/锁版本/vermin/老API/冒烟)均有对应任务;定位仅 offset(已声明范围外项)。
- **占位符**:无 TBD/TODO;所有代码完整。
- **类型一致性**:`Event` 字段、`execute_script(script, window, executor, sleep)` 签名、`VLMClient.chat(messages)`、`find_window(title_re, windows)` 各任务间一致;`WindowInfo.as_dict()` 被 recorder 使用。
