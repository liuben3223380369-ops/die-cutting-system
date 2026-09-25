"""FastAPI 应用入口"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import __version__
from app.api import api_router
from app.core.config import get_settings
from app.schemas.common import APIErrorResponse, ErrorDetail


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    data_dir = Path("./data")
    data_dir.mkdir(parents=True, exist_ok=True)
    settings = get_settings()
    if settings.is_development:
        # 开发环境：自动建表（生产请用 Alembic）
        try:
            from app.core.database import Base, engine
            import app.models  # noqa: F401
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception as e:
            print(f"[startup] auto create_all skipped: {e}")
    yield


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="模切流程系统 - 首版（非ERP定位，聚焦模切核心流程）",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(api_router)

    # ---------- 全局异常处理 ----------
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=APIErrorResponse(
                code=exc.status_code,
                message=str(exc.detail),
            ).model_dump(mode="json"),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        details = [
            ErrorDetail(
                field=".".join(str(loc) for loc in err.get("loc", [])),
                message=err.get("msg", "validation error"),
            )
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=APIErrorResponse(
                code=422,
                message="请求参数校验失败",
                details=details,
            ).model_dump(mode="json"),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # 生产环境可隐藏细节
        message = str(exc) if settings.debug else "服务器内部错误"
        return JSONResponse(
            status_code=500,
            content=APIErrorResponse(
                code=500,
                message=message,
            ).model_dump(mode="json"),
        )

    return app


app = create_app()
