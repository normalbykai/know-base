from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ParserResult:
    """解析器的原始响应与 Markdown；标准化由独立 Normalizer 完成。"""
    raw_json: dict[str, Any]
    markdown: str
    parser_version: str | None = None


class Parser(ABC):
    """所有文档解析引擎必须实现的统一边界。"""
    name: str

    @abstractmethod
    def parse(self, filename: str, content_type: str, source: bytes) -> ParserResult: ...
    # 传递文件名和 MIME 类型，便于解析器选择正确的解析策略。
