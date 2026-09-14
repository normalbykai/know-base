import uvicorn

from app.core.config import get_settings


def main() -> None:
    """统一从环境配置启动 API；使用导入字符串以支持开发热更新。"""
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )


if __name__ == "__main__":
    main()
