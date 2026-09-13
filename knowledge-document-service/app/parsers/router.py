from app.parsers.base import Parser
from app.parsers.mineru import MinerUParser


class ParserRouter:
    """集中选择解析器，禁止 API 和业务服务直接依赖具体引擎。"""
    def resolve(self, content_type: str, filename: str) -> Parser:
        """按文件类型路由；后续 Excel/HTML/邮件解析器在此扩展。"""
        # MinerU currently owns PDF and Office parsing. Extend this router, not API code.
        return MinerUParser()
