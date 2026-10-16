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
