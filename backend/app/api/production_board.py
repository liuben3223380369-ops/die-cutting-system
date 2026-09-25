"""生产看板 API"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import APIResponse
from app.services.production_board import ProductionBoardService

router = APIRouter(prefix="/production", tags=["生产看板"])


@router.get("/board", response_model=APIResponse[Any])
async def production_board(
    status: Optional[str] = Query(None, description="过滤状态，空=在制"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    svc = ProductionBoardService(db)
    data = await svc.board(status=status, limit=limit)
    return APIResponse(data=data)
