"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from backend.api import system
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
        title="Mobile Zhongkong",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(system.router)
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
