import pytest

from common.vlmclient import VLMClient, VLMError, extract_json, image_data_url


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


def test_extract_json_multi_fence_picks_first_parseable():
    text = ("错误示例:\n```json\n{\"bad\": }\n```\n"
            "正确脚本:\n```json\n{\"name\": \"d\", \"steps\": []}\n```")
    assert extract_json(text) == {"name": "d", "steps": []}


def test_extract_json_fence_without_json_label():
    assert extract_json("结果:\n```\n{\"a\": 1}\n```") == {"a": 1}


def test_chat_sends_max_tokens_when_configured(monkeypatch):
    import common.vlmclient as v
    seen = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(json)
        return _Resp({"choices": [{"message": {"content": "x"}}]})

    monkeypatch.setattr(v.requests, "post", fake_post)
    c = v.VLMClient({"base_url": "https://x", "api_key": "k", "model": "m",
                     "timeout_seconds": 5, "max_tokens": 8192})
    c.chat([{"role": "user", "content": "hi"}])
    assert seen["max_tokens"] == 8192


def test_chat_omits_max_tokens_when_unset(monkeypatch):
    import common.vlmclient as v
    seen = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen.update(json)
        return _Resp({"choices": [{"message": {"content": "x"}}]})

    monkeypatch.setattr(v.requests, "post", fake_post)
    c = v.VLMClient({"base_url": "https://x", "api_key": "k",
                     "model": "m", "timeout_seconds": 5})
    c.chat([{"role": "user", "content": "hi"}])
    assert "max_tokens" not in seen


def test_chat_http_error_becomes_vlm_error(monkeypatch):
    import common.vlmclient as v

    class _BadResp(object):
        def raise_for_status(self):
            raise v.requests.HTTPError("401 Client Error")

    monkeypatch.setattr(v.requests, "post", lambda *a, **kw: _BadResp())
    c = v.VLMClient({"base_url": "https://x", "api_key": "k",
                     "model": "m", "timeout_seconds": 5})
    with pytest.raises(VLMError):
        c.chat([{"role": "user", "content": "hi"}])


def test_chat_timeout_becomes_vlm_error(monkeypatch):
    import common.vlmclient as v

    def fake_post(url, headers=None, json=None, timeout=None):
        raise v.requests.Timeout("timed out")

    monkeypatch.setattr(v.requests, "post", fake_post)
    c = v.VLMClient({"base_url": "https://x", "api_key": "k",
                     "model": "m", "timeout_seconds": 5})
    with pytest.raises(VLMError, match="VLM 请求失败"):
        c.chat([{"role": "user", "content": "hi"}])


def test_chat_empty_content_reports_finish_reason(monkeypatch):
    import common.vlmclient as v

    monkeypatch.setattr(v.requests, "post", lambda *a, **kw: _Resp(
        {"choices": [{"message": {"content": None},
                      "finish_reason": "length"}]}))
    c = v.VLMClient({"base_url": "https://x", "api_key": "k",
                     "model": "m", "timeout_seconds": 5})
    with pytest.raises(VLMError, match="finish_reason='length'"):
        c.chat([{"role": "user", "content": "hi"}])


def test_image_data_url_returns_png_data_url(tmp_path):
    from PIL import Image
    img = Image.new("RGB", (2000, 100))
    path = tmp_path / "shot.png"
    img.save(str(path))
    url = image_data_url(str(path))
    assert url.startswith("data:image/png;base64,")
    assert len(url) > len("data:image/png;base64,")
