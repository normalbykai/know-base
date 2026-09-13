import httpx

from app.core.config import get_settings
from app.parsers.base import Parser, ParserResult


class MinerUParser(Parser):
    """独立部署的 MinerU HTTP 适配器，避免 API 进程承载模型/GPU。"""

    name = "mineru"

    def parse(self, filename: str, content_type: str, source: bytes) -> ParserResult:
        """提交文件并将 MinerU 响应收敛为内部 ParserResult。"""
        settings = get_settings()
        try:
            response = httpx.post(
                f"{settings.mineru_base_url.rstrip('/')}/parse",
                files={"file": (filename, source, content_type)},
                timeout=300,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # 对外只记录可读错误；worker 会把任务转为 FAILED，供用户重试。
            raise RuntimeError(f"MinerU service unavailable or parsing request failed: {exc}") from exc
        payload = response.json()
        return ParserResult(
            raw_json=payload,
            markdown=payload.get("markdown", ""),
            parser_version=payload.get("parser_version"),
        )
