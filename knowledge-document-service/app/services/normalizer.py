import re
from typing import Any

from app.schemas.document import DocumentBlock, DocumentModel


class DocumentNormalizer:
    """将解析器私有输出转换为稳定的 DocumentModel 中文间层。"""

    def normalize(self, document_id: str, filename: str, content_type: str, raw: dict[str, Any], markdown: str) -> DocumentModel:
        """优先保留结构化块；无结构化块时降级从 Markdown 构造可检索块。"""
        blocks: list[DocumentBlock] = []
        source_blocks = raw.get("blocks") or raw.get("content_list") or []
        for index, item in enumerate(source_blocks, start=1):
            # 块 ID 由标准化层稳定生成，避免下游依赖解析器的临时 ID。
            kind = self._kind(item)
            if kind is None:
                continue
            text = item.get("text") or item.get("content") or item.get("text_content")
            blocks.append(DocumentBlock(
                id=f"block_{index:04d}", type=kind, page=item.get("page") or item.get("page_idx"),
                level=item.get("level"), text=text if kind not in {"table", "image"} else None,
                content=text if kind in {"table", "image"} else None,
            ))
        if not blocks and markdown:
            blocks = self._markdown_blocks(markdown)
        return DocumentModel(
            document_id=document_id,
            title=raw.get("title") or filename.rsplit(".", 1)[0],
            metadata={"filename": filename, "content_type": content_type, "page_count": raw.get("page_count")},
            blocks=blocks,
        )

    @staticmethod
    def _kind(item: dict[str, Any]) -> str | None:
        """把不同解析器的类型名折叠为 DocumentModel 支持的有限集合。"""
        value = str(item.get("type") or item.get("category") or "text").lower()
        mapping = {"title": "heading", "heading": "heading", "text": "paragraph", "paragraph": "paragraph", "table": "table", "image": "image", "list": "list", "code": "code"}
        return mapping.get(value, "paragraph")

    @staticmethod
    def _markdown_blocks(markdown: str) -> list[DocumentBlock]:
        """兼容只返回 Markdown 的解析器；标题层级仍可被后续 Chunk 使用。"""
        blocks = []
        for index, line in enumerate((line for line in markdown.splitlines() if line.strip()), start=1):
            match = re.match(r"^(#{1,6})\s+(.*)", line)
            blocks.append(DocumentBlock(id=f"block_{index:04d}", type="heading" if match else "paragraph", level=len(match.group(1)) if match else None, text=match.group(2) if match else line))
        return blocks
