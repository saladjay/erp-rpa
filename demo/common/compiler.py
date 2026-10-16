# -*- coding: utf-8 -*-
"""会话 → 确定性脚本 编译器。大模型只在这里出现(共识:LLM 仅创作期)。"""
import json
import os

from common.events import merge_key_runs, read_events
from common.script import validate
from common.vlmclient import extract_json, image_data_url

MAX_IMAGES = 20

BUTTON_NAMES = {"left": "左", "right": "右", "middle": "中"}

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
5. target.title_re 用宽松正则匹配窗口标题(标题可能带文件名,如 "xxx - 记事本")。
6. 时间线中单独出现的 shift/ctrl/alt 是修饰键按下,不是独立操作——忽略它们,不要为单独修饰键生成任何步骤;hotkey 的 keys 用小写键名(如 ["ctrl","s"])。
7. locator 的 x/y 就是时间线给出的 win_rel=(x,y) 中的两个数,原样填入。
8. input 的 text 必须逐字来自时间线的"输入文本",禁止改写、增删空格或标点。"""


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
            lines.append('[%d] t=%.1fs %s键点击 abs=(%s,%s) %s 窗口="%s"'
                         % (ev.index, ev.t,
                            BUTTON_NAMES.get(ev.button, ev.button or "左"),
                            ev.x, ev.y, rel, (w.get("title") or "")[:30]))
        elif ev.type == "key":
            if ev.text is not None:
                lines.append("[%d] t=%.1fs 输入文本 %r" % (ev.index, ev.t, ev.text))
            else:
                lines.append("[%d] t=%.1fs 按键 %s" % (ev.index, ev.t, ev.key))
    return lines


def compile_session(session_dir, client, out_path=None):
    events = merge_key_runs(read_events(session_dir))
    intent_path = os.path.join(session_dir, "intent.txt")
    with open(intent_path, "r", encoding="utf-8-sig") as f:
        intent = f.read().strip()
    if not intent:
        raise ValueError("intent.txt 为空,请说明操作意图")

    shots = [ev.screenshot for ev in events if ev.screenshot][:MAX_IMAGES]
    text_part = ("操作意图:%s\n\n事件时间线:\n%s\n\n请输出脚本 JSON。"
                 % (intent, "\n".join(event_lines(events))))
    content = [{"type": "text", "text": text_part}]
    for s in shots:
        p = os.path.join(session_dir, s)
        if not os.path.exists(p):
            continue
        try:
            url = image_data_url(p)
        except Exception:
            continue  # 损坏/截断的截图跳过,与 events.jsonl 断尾容错策略对称
        content.append({"type": "image_url", "image_url": {"url": url}})

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
