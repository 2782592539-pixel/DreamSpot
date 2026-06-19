"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.api import system, tasks
from backend.config import get_settings
from backend.db.init_db import init_db
from backend.services.executor import TaskExecutor
from backend.services.scheduler import MzcScheduler

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger.info("MZC service starting (version=0.1.0)")

    # Ensure DB schema exists (idempotent)
    init_db()

    # Start scheduler with executor as tick handler
    executor = TaskExecutor()
    scheduler = MzcScheduler()
    scheduler.set_tick_handler(executor.tick)
    scheduler.start()
    scheduler.reload_tasks()
    app.state.scheduler = scheduler
    app.state.executor = executor

    try:
        yield
    finally:
        scheduler.shutdown()
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
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR)), name="assets")

    @app.get("/", include_in_schema=False)
    def home() -> HTMLResponse:
        return HTMLResponse(INDEX_HTML.read_text(encoding="utf-8"))

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
