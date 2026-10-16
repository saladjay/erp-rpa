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
