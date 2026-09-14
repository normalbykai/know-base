import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.parsers.base import Parser, ParserResult


class MinerUParser(Parser):
    """适配 MinerU 官方 Web API，避免业务代码依赖其响应协议。"""

    name = "mineru"

    def parse(self, filename: str, content_type: str, source: bytes) -> ParserResult:
        """调用同步接口并将 ``results`` 中的单文件结果转换为内部契约。"""
        settings = get_settings()
        try:
            response = httpx.post(
                f"{settings.mineru_base_url.rstrip('/')}/file_parse",
                # MinerU 的字段名是 files（复数）；要求 content_list 才能供标准化层保留版面结构。
                files=[("files", (filename, source, content_type))],
                data={"return_md": "true", "return_content_list": "true", "response_format_zip": "false"},
                timeout=300,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # 对外只记录可读错误；worker 会把任务转为 FAILED，供用户重试。
            raise RuntimeError(f"MinerU service unavailable or parsing request failed: {exc}") from exc
        try:
            payload: dict[str, Any] = response.json()
            result = self._single_result(payload)
        except (AttributeError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError("MinerU returned an invalid parsing response") from exc

        content_list = result.get("content_list") or []
        if isinstance(content_list, str):
            try:
                content_list = json.loads(content_list)
            except json.JSONDecodeError as exc:
                raise RuntimeError("MinerU returned invalid content_list JSON") from exc
        if not isinstance(content_list, list):
            raise RuntimeError("MinerU returned content_list in an unsupported format")
        return ParserResult(
            # 仅向 Normalizer 暴露稳定字段；原始 MinerU 协议仍保存在 parser_response 以便排障。
            raw_json={"title": filename.rsplit(".", 1)[0], "content_list": content_list, "parser_response": payload},
            markdown=str(result.get("md_content") or ""),
            parser_version=str(payload["version"]) if payload.get("version") is not None else None,
        )

    @staticmethod
    def _single_result(payload: dict[str, Any]) -> dict[str, Any]:
        """当前一次仅提交一个文件，拒绝缺失或歧义结果，避免保存错文档。"""
        results = payload.get("results")
        if not isinstance(results, dict) or len(results) != 1:
            raise RuntimeError("MinerU response does not contain exactly one file result")
        result = next(iter(results.values()))
        if not isinstance(result, dict):
            raise RuntimeError("MinerU file result has an unsupported format")
        return result
