"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from backend.api import system, tasks
from backend.config import get_settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("MZC service starting (version=0.1.0)")
    yield
    logger.info("MZC service stopping")


def create_app() -> FastAPI:
    app = FastAPI(
        title="MZC 移动中控",
        version="0.1.0",
        description="家用 Claude Code 移动控制中心",
        openapi_tags=[
            {"name": "服务状态", "description": "MZC 服务自身的健康与状态接口"},
            {"name": "定时任务", "description": "从 Claude Code 同步的定时任务管理接口"},
        ],
        docs_url=None,    # 关闭默认 Swagger UI
        redoc_url=None,   # 关闭默认 ReDoc
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    app.include_router(system.router)
    app.include_router(tasks.router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
