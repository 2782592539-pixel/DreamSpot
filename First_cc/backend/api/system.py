"""服务状态相关接口。"""
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(
    prefix="/api/system",
    tags=["服务状态"],
)


@router.get("/status", summary="获取服务状态", description="检查 MZC 服务是否在线,返回版本号与时间戳。")
def get_status() -> dict:
    """Return service health status."""
    return {
        "status": "ok",
        "service": "mzc",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
