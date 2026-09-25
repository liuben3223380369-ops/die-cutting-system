"""期间锁定 API"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import APIResponse
from app.services.period import PeriodError, PeriodService

router = APIRouter(prefix="/periods", tags=["期间结账"])


class PeriodAction(BaseModel):
    year: int = Field(..., ge=2000, le=2100)
    month: int = Field(..., ge=1, le=12)
    remark: Optional[str] = None


class PeriodOut(BaseModel):
    id: int
    year: int
    month: int
    status: str
    locked_at: Optional[str] = None
    locked_by: Optional[str] = None
    remark: Optional[str] = None

    model_config = {"from_attributes": True}


def _out(p) -> PeriodOut:
    return PeriodOut(
        id=p.id,
        year=p.year,
        month=p.month,
        status=p.status,
        locked_at=p.locked_at.isoformat() if p.locked_at else None,
        locked_by=p.locked_by,
        remark=p.remark,
    )


@router.get("", response_model=APIResponse[List[PeriodOut]])
async def list_periods(year: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    svc = PeriodService(db)
    items = await svc.list_periods(year)
    return APIResponse(data=[_out(p) for p in items])


@router.post("/lock", response_model=APIResponse[PeriodOut])
async def lock_period(body: PeriodAction, db: AsyncSession = Depends(get_db)):
    svc = PeriodService(db)
    try:
        p = await svc.lock_period(body.year, body.month, body.remark)
        return APIResponse(data=_out(p))
    except PeriodError as e:
        raise HTTPException(400, str(e))


@router.post("/unlock", response_model=APIResponse[PeriodOut])
async def unlock_period(body: PeriodAction, db: AsyncSession = Depends(get_db)):
    svc = PeriodService(db)
    try:
        p = await svc.unlock_period(body.year, body.month)
        return APIResponse(data=_out(p))
    except PeriodError as e:
        raise HTTPException(400, str(e))


@router.get("/check", response_model=APIResponse[dict])
async def check_period(
    year: int,
    month: int,
    db: AsyncSession = Depends(get_db),
):
    from datetime import date

    svc = PeriodService(db)
    locked = await svc.is_locked(date(year, month, 1))
    return APIResponse(data={"year": year, "month": month, "locked": locked})
