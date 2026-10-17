import json
import os

import pytest
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


# 模拟 E2E 实测的坏输出:hotkey keys 缺了引号(s" 处)
BAD_JSON = ('```json\n{"name": "x", "target": {"title_re": "t"}, '
            '"steps": [{"action": "hotkey", "keys": ["ctrl",s"]}]}\n```')


class RetryClient(object):
    """按顺序返回预设回复,记录每次调用收到的消息(模拟解析失败重试)。"""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def chat(self, messages):
        self.calls.append(messages)
        return self.replies.pop(0)


def test_event_lines_click_contains_win_rel():
    ev = Event(index=3, t=2.5, type="click", x=300, y=200, button="left",
               window={"left": 100, "top": 50, "title": "记事本"})
    assert "win_rel=(200,150)" in event_lines([ev])[0]
    assert "左键点击" in event_lines([ev])[0]
    right = Event(index=4, t=3.0, type="click", x=10, y=10, button="right",
                  window={"left": 0, "top": 0, "title": "t"})
    assert "右键点击" in event_lines([right])[0]
    odd = Event(index=5, t=3.5, type="click", x=10, y=10, button="xbutton1",
                window={"left": 0, "top": 0, "title": "t"})
    assert "xbutton1键点击" in event_lines([odd])[0]


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
    with pytest.raises(ValueError):
        compile_session(d, FakeClient(bad))


def _make_click_session(tmp_path, shot_indexes):
    """25 个点击事件,只有 shot_indexes 里的事件带有效截图。"""
    d = str(tmp_path)
    for i in range(25):
        shot = "shot_%03d.png" % i if i in shot_indexes else None
        if shot:
            Image.new("RGB", (10, 10), "white").save(os.path.join(d, shot))
        write_event(d, Event(index=i, t=0.5 + i, type="click", x=100 + i, y=200,
                             button="left", screenshot=shot,
                             window={"left": 100, "top": 50, "title": "记事本"}))
    with open(os.path.join(d, "intent.txt"), "w", encoding="utf-8") as f:
        f.write("在记事本里输入问候语")
    return d


def test_compile_session_caps_images_at_max(tmp_path):
    # 末条事件无截图 → 不触发补图,恰好 MAX_IMAGES 张
    d = _make_click_session(tmp_path, shot_indexes=range(20))
    fake = FakeClient(VALID_SCRIPT)
    compile_session(d, fake)
    kinds = [c["type"] for c in fake.messages[1]["content"]]
    assert kinds.count("image_url") == 20  # MAX_IMAGES 上限锁定


def test_compile_session_appends_final_screenshot(tmp_path):
    # 前 20 有截图、第 25 条也有 → 前 20 + 末条补回,恰 21 张(至多 MAX_IMAGES+1)
    d = _make_click_session(tmp_path, shot_indexes=list(range(20)) + [24])
    fake = FakeClient(VALID_SCRIPT)
    compile_session(d, fake)
    kinds = [c["type"] for c in fake.messages[1]["content"]]
    assert kinds.count("image_url") == 21


def test_compile_session_skips_corrupt_screenshot(tmp_path):
    d = str(tmp_path)
    write_event(d, Event(index=0, t=0.5, type="click", x=300, y=200,
                         button="left", screenshot="shot_good.png",
                         window={"left": 100, "top": 50, "title": "记事本"}))
    write_event(d, Event(index=1, t=1.0, type="click", x=400, y=250,
                         button="right", screenshot="shot_bad.png",
                         window={"left": 100, "top": 50, "title": "记事本"}))
    Image.new("RGB", (10, 10), "white").save(os.path.join(d, "shot_good.png"))
    with open(os.path.join(d, "shot_bad.png"), "wb") as f:
        f.write(b"this is garbage, not a png at all")
    with open(os.path.join(d, "intent.txt"), "w", encoding="utf-8") as f:
        f.write("在记事本里输入问候语")
    fake = FakeClient(VALID_SCRIPT)
    out = compile_session(d, fake)
    assert out.endswith("script.json")  # 坏图跳过,编译不崩
    kinds = [c["type"] for c in fake.messages[1]["content"]]
    assert kinds.count("image_url") == 1  # 好图保留,坏图丢弃


def test_compile_session_repairs_bad_json_once(tmp_path):
    d = _make_session(tmp_path)
    good = "```json\n" + json.dumps(VALID_SCRIPT, ensure_ascii=False) + "\n```"
    client = RetryClient([BAD_JSON, good])
    out = compile_session(d, client)
    assert out.endswith("script.json")
    assert len(client.calls) == 2  # 坏 JSON 触发一次重试
    retry_msg = client.calls[1][-1]
    assert retry_msg["role"] == "user"
    assert "不是合法 JSON" in retry_msg["content"]
    assert "上一次的输出" in retry_msg["content"]


def test_compile_session_two_bad_json_raises(tmp_path):
    d = _make_session(tmp_path)
    client = RetryClient([BAD_JSON, "完全不是 JSON"])
    with pytest.raises(ValueError):
        compile_session(d, client)
    assert len(client.calls) == 2  # 只重试一次,不再三连调


def test_system_prompt_states_schema():
    assert "title_re" in SYSTEM_PROMPT and "win_rel" in SYSTEM_PROMPT
    assert "修饰键" in SYSTEM_PROMPT       # 规则6:单独 shift/ctrl/alt 不生成步骤
    assert "原样填入" in SYSTEM_PROMPT     # 规则7:win_rel 直接进 locator
    assert "逐字" in SYSTEM_PROMPT         # 规则8:input 文本逐字照抄
    assert "目标窗口" in SYSTEM_PROMPT     # 规则9:丢弃其他窗口的启动步骤
    assert "禁止发明" in SYSTEM_PROMPT     # 规则10:不发明未演示的步骤
    assert "上屏" in SYSTEM_PROMPT         # 规则11:IME 拼音以最终上屏为准
    assert "锚定" in SYSTEM_PROMPT         # 规则5:不要用 ^ 和 $ 锚定标题
