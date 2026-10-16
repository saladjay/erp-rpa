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
        self.max_tokens = cfg.get("max_tokens")

    def chat(self, messages):
        url = self.base_url + "/chat/completions"
        headers = {"Authorization": "Bearer " + self.api_key}
        payload = {"model": self.model, "messages": messages}
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens
        try:
            r = requests.post(url, headers=headers, json=payload,
                              timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as exc:
            raise VLMError("VLM 请求失败: %s" % exc)
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
        except (KeyError, IndexError):
            content = None
            finish_reason = None
        if not content:
            raise VLMError("VLM 空回复: finish_reason=%r, raw=%s"
                           % (finish_reason,
                              json.dumps(data, ensure_ascii=False)[:500]))
        return content


def extract_json(text):
    """从模型回复中剥掉 ```json 围栏/前后闲话,解析出 JSON 对象。

    思考类模型可能先输出错误示例再给最终脚本,故遍历所有围栏块,
    第一个能解析成功的 JSON 胜出;全部失败再回退到"首个 { 到
    最后一个 }"的截取,仍失败抛 ValueError。"""
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S):
        try:
            return json.loads(m.group(1))
        except ValueError:
            continue
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
