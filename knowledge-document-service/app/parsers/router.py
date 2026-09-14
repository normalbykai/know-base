from app.parsers.base import Parser
from app.parsers.deepseek_vision import DeepSeekVisionParser
from app.parsers.mineru import MinerUParser
from app.core.config import get_settings


class ParserRouter:
    """集中选择解析器，禁止 API 和业务服务直接依赖具体引擎。"""
    def resolve(self, content_type: str, filename: str) -> Parser:
        """按文件类型路由；后续 Excel/HTML/邮件解析器在此扩展。"""
        # 解析器由环境变量选择；默认云端模型，本地 MinerU 保留为私有化/高精度备用方案。
        parser = get_settings().document_parser.lower()
        if parser == "deepseek_vision":
            return DeepSeekVisionParser()
        if parser == "mineru":
            return MinerUParser()
        raise ValueError("DOCUMENT_PARSER must be deepseek_vision or mineru")
