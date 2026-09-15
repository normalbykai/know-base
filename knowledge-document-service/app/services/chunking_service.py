import math
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import DocumentVersion
from app.models.document_chunk import DocumentChunk
from app.schemas.document import DocumentBlock, DocumentModel


@dataclass(frozen=True)
class ChunkDraft:
    """尚未持久化的分块，避免分块算法直接依赖数据库实现。"""
    content: str
    heading_path: str | None
    page_start: int | None
    page_end: int | None


class DocumentChunker:
    """按标题上下文和受控长度将标准 DocumentModel 转为可检索片段。"""

    def __init__(self, max_characters: int = 1200) -> None:
        self.max_characters = max_characters

    def chunk(self, model: DocumentModel) -> list[ChunkDraft]:
        """标题更新路径、内容块按页与长度聚合；表格、图片、代码独立保留。"""
        drafts: list[ChunkDraft] = []
        headings: dict[int, str] = {}
        pending: list[tuple[str, int | None]] = []

        def flush() -> None:
            if not pending:
                return
            content = "\n\n".join(value for value, _ in pending).strip()
            pages = [page for _, page in pending if page is not None]
            if content:
                drafts.append(ChunkDraft(content, self._heading_path(headings), min(pages) if pages else None, max(pages) if pages else None))
            pending.clear()

        for block in model.blocks:
            if block.type == "heading":
                flush()
                heading = self._block_content(block)
                if heading:
                    level = max(1, min(block.level or 1, 6))
                    headings[level] = heading
                    for stale_level in [key for key in headings if key > level]:
                        del headings[stale_level]
                continue
            content = self._block_content(block)
            if not content:
                continue
            # 结构化内容独立成块，避免 Markdown 表格和代码与自然段混杂后失去可读性。
            if block.type in {"table", "image", "code"}:
                flush()
                for part in self._split(content):
                    drafts.append(ChunkDraft(part, self._heading_path(headings), block.page, block.page))
                continue
            for part in self._split(content):
                pending_size = sum(len(value) for value, _ in pending) + max(0, len(pending) * 2)
                if pending and pending_size + len(part) > self.max_characters:
                    flush()
                pending.append((part, block.page))
        flush()
        # 极少数空白解析结果仍写入标题占位块，使历史回填具备严格幂等性并便于质量排查。
        if not drafts and model.title.strip():
            drafts.append(ChunkDraft(model.title.strip(), None, None, None))
        return drafts

    def _split(self, content: str) -> list[str]:
        """优先按句末或换行切分超长块，必要时按字符硬切，确保不会丢失正文。"""
        value = re.sub(r"\s+", " ", content).strip()
        if len(value) <= self.max_characters:
            return [value]
        parts: list[str] = []
        remaining = value
        while len(remaining) > self.max_characters:
            boundary = max(remaining.rfind(mark, 0, self.max_characters) for mark in "。！？；.!?;\n")
            boundary = boundary + 1 if boundary >= self.max_characters // 2 else self.max_characters
            parts.append(remaining[:boundary].strip())
            remaining = remaining[boundary:].strip()
        if remaining:
            parts.append(remaining)
        return parts

    @staticmethod
    def _block_content(block: DocumentBlock) -> str:
        return (block.content or block.text or "").strip()

    @staticmethod
    def _heading_path(headings: dict[int, str]) -> str | None:
        return " > ".join(headings[level] for level in sorted(headings)) or None

    @staticmethod
    def token_estimate(content: str) -> int:
        """在尚未绑定具体 Embedding 模型前使用稳定的保守估算。"""
        return max(1, math.ceil(len(content) / 3))


class DocumentChunkService:
    """统一持久化分块，确保实时解析和历史回填使用完全相同的规则。"""

    def __init__(self, db: Session, max_characters: int = 1200) -> None:
        self.db = db
        self.chunker = DocumentChunker(max_characters)

    def version_has_chunks(self, document_version_id: str) -> bool:
        """通过任意一个分块判断版本是否已处理，用于幂等回填。"""
        return self.db.scalar(select(DocumentChunk.id).where(DocumentChunk.document_version_id == document_version_id).limit(1)) is not None

    def add_version_chunks(self, version: DocumentVersion, model: DocumentModel) -> list[DocumentChunk]:
        """生成版本内稳定序号并加入当前事务；提交由上层业务流程控制。"""
        chunks = [
            DocumentChunk(
                document_id=version.document_id,
                document_version_id=version.id,
                chunk_index=index,
                content=draft.content,
                heading_path=draft.heading_path,
                page_start=draft.page_start,
                page_end=draft.page_end,
                character_count=len(draft.content),
                token_estimate=self.chunker.token_estimate(draft.content),
            )
            for index, draft in enumerate(self.chunker.chunk(model))
        ]
        self.db.add_all(chunks)
        return chunks
