import httpx

from app.parsers.deepseek_vision import DeepSeekVisionParser


def test_deepseek_vision_parser_sends_openai_compatible_image_request(monkeypatch) -> None:
    """云端解析器应仅通过认证头传递 Key，并将模型响应收敛为页级 JSON。"""
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, json={"choices": [{"message": {"content": '{"markdown":"正文","blocks":[{"type":"paragraph","text":"正文"}]}'}}]})

    monkeypatch.setattr("app.parsers.deepseek_vision.httpx.post", fake_post)
    parsed = DeepSeekVisionParser._parse_page("https://example.test/v1", "secret", "vision-model", "image/png", b"image", 1)

    assert captured["url"] == "https://example.test/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["json"]["model"] == "vision-model"
    assert captured["json"]["thinking"] == {"type": "disabled"}
    assert captured["json"]["response_format"] == {"type": "json_object"}
    assert parsed["blocks"][0]["text"] == "正文"
