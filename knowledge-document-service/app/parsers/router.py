from app.parsers.base import Parser
from app.parsers.deepseek_vision import DeepSeekVisionParser
from app.parsers.mineru import MinerUParser
from app.core.config import get_settings


class ParserRouter:
    """集中选择解析器，禁止 API 和业务服务直接依赖具体引擎。"""
    def resolve(self, content_type: str, filename: str, parser_name: str | None = None) -> Parser:
        """按任务已记录的解析器路由；旧任务不受之后配置变更影响。"""
        # 解析器由环境变量选择；默认云端模型，本地 MinerU 保留为私有化/高精度备用方案。
        parser = (parser_name or get_settings().document_parser).lower()
        if parser == "deepseek_vision":
            return DeepSeekVisionParser()
        if parser == "mineru":
            return MinerUParser()
        raise ValueError("DOCUMENT_PARSER must be deepseek_vision or mineru")
