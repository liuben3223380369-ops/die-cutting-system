"""健康检查接口"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import get_settings
from app.core.database import get_db
from app.schemas.common import APIResponse, HealthStatus

router = APIRouter(tags=["健康检查"])


@router.get("/health", response_model=APIResponse[HealthStatus])
async def health_check(db: AsyncSession = Depends(get_db)):
    """系统健康检查"""
    settings = get_settings()
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    data = HealthStatus(
        status="ok" if db_status == "ok" else "degraded",
        app_name=settings.app_name,
        version=__version__,
        environment=settings.app_env,
        database=db_status,
    )
    return APIResponse(data=data)
