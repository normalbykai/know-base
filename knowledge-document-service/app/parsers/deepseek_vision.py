import base64
import json
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.parsers.base import Parser, ParserResult


SYSTEM_PROMPT = """你是企业文档解析器。请只返回一个 JSON 对象，不能使用 Markdown 代码围栏。
JSON 格式必须为：
{"markdown":"本页 Markdown", "blocks":[{"type":"heading|paragraph|table|image|list|code", "text":"内容", "content":"表格或图片内容", "level":1}]}
保留原文，不要总结或补写；表格使用 Markdown 表格放入 content；每个 block 必须对应本页实际内容。"""


class DeepSeekVisionParser(Parser):
    """通过 OpenAI 兼容的视觉聊天接口解析 PDF 页或图片，避免部署本地 GPU 模型。"""

    name = "deepseek_vision"

    def parse(self, filename: str, content_type: str, source: bytes) -> ParserResult:
        """逐页请求视觉模型；单页失败即让 Worker 保留失败状态，避免保存不完整文档。"""
        settings = get_settings()
        if not settings.deepseek_api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        if not settings.deepseek_vision_model:
            raise RuntimeError("DEEPSEEK_VISION_MODEL is not configured; set it to your vision-capable model name")

        pages = self._page_images(filename, content_type, source, settings.deepseek_max_pages)
        all_blocks: list[dict[str, Any]] = []
        markdown_pages: list[str] = []
        for page_number, (mime_type, image) in enumerate(pages, start=1):
            page = self._parse_page(
                base_url=settings.deepseek_base_url,
                api_key=settings.deepseek_api_key,
                model=settings.deepseek_vision_model,
                mime_type=mime_type,
                image=image,
                page_number=page_number,
                max_output_tokens=settings.deepseek_max_output_tokens,
            )
            markdown = page.get("markdown")
            if isinstance(markdown, str) and markdown.strip():
                markdown_pages.append(markdown.strip())
            blocks = page.get("blocks")
            if not isinstance(blocks, list):
                raise RuntimeError(f"Vision model returned invalid blocks for page {page_number}")
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                # 页码由服务端附加，不能依赖模型自行猜测页码。
                all_blocks.append({**block, "page": page_number})

        return ParserResult(
            raw_json={"title": Path(filename).stem, "blocks": all_blocks, "page_count": len(pages)},
            markdown="\n\n".join(markdown_pages),
            parser_version=settings.deepseek_vision_model,
        )

    @staticmethod
    def _page_images(filename: str, content_type: str, source: bytes, max_pages: int) -> list[tuple[str, bytes]]:
        """PDF 仅在本地栅格化，不上传到第三方；最终发送的是受控页数的图片。"""
        suffix = Path(filename).suffix.lower()
        if content_type == "application/pdf" or suffix == ".pdf":
            try:
                import fitz  # PyMuPDF 仅在处理 PDF 时加载，图片解析不受该可选运行时影响。
            except ImportError as exc:
                raise RuntimeError("PyMuPDF is required for PDF vision parsing; reinstall project dependencies") from exc
            document = fitz.open(stream=source, filetype="pdf")
            try:
                if document.page_count > max_pages:
                    raise RuntimeError(f"Document has {document.page_count} pages; DEEPSEEK_MAX_PAGES is {max_pages}")
                return [("image/jpeg", page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).tobytes("jpeg")) for page in document]
            finally:
                document.close()
        if content_type.startswith("image/"):
            return [(content_type, source)]
        raise RuntimeError("DeepSeek vision parsing currently supports PDF and image files only")

    @staticmethod
    def _parse_page(base_url: str, api_key: str, model: str, mime_type: str, image: bytes, page_number: int, max_output_tokens: int = 8192) -> dict[str, Any]:
        """兼容 OpenAI 风格多模态接口；Key 仅置于 Authorization 头且不会写入任务错误。"""
        image_url = f"data:{mime_type};base64,{base64.b64encode(image).decode('ascii')}"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": f"解析第 {page_number} 页。"},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]},
            ],
            "temperature": 0,
            # 文档转写是确定性提取任务；关闭默认高强度思考，避免推理 token 挤占结构化输出额度。
            "thinking": {"type": "disabled"},
            # 官方 JSON Output 可确保 Worker 无需猜测或修复模型生成的结构化结果。
            "response_format": {"type": "json_object"},
            "max_tokens": max_output_tokens,
        }
        try:
            response = httpx.post(
                f"{base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
                timeout=120,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("content is not text")
            return json.loads(DeepSeekVisionParser._strip_fence(content))
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"DeepSeek vision parsing failed for page {page_number}: {exc}") from exc

    @staticmethod
    def _strip_fence(content: str) -> str:
        """容忍少数模型仍返回 JSON 代码围栏，但不会尝试修复非 JSON 的生成内容。"""
        value = content.strip()
        if value.startswith("```") and value.endswith("```"):
            return value.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return value
