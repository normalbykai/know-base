import json

import httpx

from app.parsers.mineru import MinerUParser


def test_mineru_parser_adapts_official_file_parse_response(monkeypatch) -> None:
    """官方 API 的 results/content_list 需要在解析器边界转换为项目内部格式。"""
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        request = httpx.Request("POST", url)
        return httpx.Response(200, request=request, json={
            "version": "3.4.5",
            "results": {"handbook": {"md_content": "# 员工手册", "content_list": json.dumps([{"type": "text", "text": "欢迎"}])}},
        })

    monkeypatch.setattr("app.parsers.mineru.httpx.post", fake_post)
    parsed = MinerUParser().parse("handbook.pdf", "application/pdf", b"pdf")

    assert captured["url"].endswith("/file_parse")
    assert captured["data"]["return_content_list"] == "true"
    assert parsed.markdown == "# 员工手册"
    assert parsed.raw_json["content_list"] == [{"type": "text", "text": "欢迎"}]
    assert parsed.parser_version == "3.4.5"
