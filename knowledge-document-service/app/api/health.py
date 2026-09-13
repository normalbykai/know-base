from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """供容器探针和部署平台检查 API 进程是否存活。"""
    return {"status": "ok"}
