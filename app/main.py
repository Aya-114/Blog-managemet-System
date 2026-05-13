import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import configure_logging
from app.db.session import create_db_and_tables
from app.routes import admin_users, auth, comments, monitoring, posts
from app.services.metrics import metrics_store

logger = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent / "static"


def create_app() -> FastAPI:
    configure_logging()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        create_db_and_tables()
        yield

    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description="FastAPI backend for a blog platform with JWT auth, RBAC, Redis caching, and monitoring.",
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            metrics_store.record_request(request.method, request.url.path, 500, duration_ms)
            metrics_store.record_error(request.method, request.url.path, str(exc))
            logger.exception(
                "Unhandled request error",
                extra={"method": request.method, "path": request.url.path, "duration_ms": round(duration_ms, 2)},
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        metrics_store.record_request(request.method, request.url.path, response.status_code, duration_ms)
        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            },
        )
        return response

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(
            "Validation error",
            extra={"method": request.method, "path": request.url.path, "operation": "validation"},
        )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    application.include_router(auth.router, prefix=settings.api_prefix)
    application.include_router(admin_users.router, prefix=settings.api_prefix)
    application.include_router(posts.router, prefix=settings.api_prefix)
    application.include_router(comments.router, prefix=settings.api_prefix)
    application.include_router(monitoring.router, prefix=settings.api_prefix)

    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @application.get("/", include_in_schema=False)
    def frontend():
        return FileResponse(STATIC_DIR / "index.html")

    @application.get("/dashboard", include_in_schema=False)
    def dashboard():
        return FileResponse(STATIC_DIR / "dashboard.html")

    return application


app = create_app()
