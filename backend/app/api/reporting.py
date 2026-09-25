"""统计与 Excel 导出 API"""
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.common import APIResponse
from app.services.reporting import ReportingService

router = APIRouter(prefix="/reports", tags=["统计报表"])


@router.get("/daily", response_model=APIResponse[Any])
async def daily_report(
    report_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    """日报（统一指标）"""
    d = report_date or date.today()
    svc = ReportingService(db)
    data = await svc.daily_report(d)
    return APIResponse(data=data)


@router.get("/period", response_model=APIResponse[Any])
async def period_report(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """自定义区间报表（与日报同一套指标）"""
    if end_date < start_date:
        raise HTTPException(400, "结束日期不能早于开始日期")
    svc = ReportingService(db)
    data = await svc.period_report(start_date, end_date)
    return APIResponse(data=data)


@router.get("/ledgers", response_model=APIResponse[Any])
async def ledger_detail(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    source_type: Optional[str] = None,
    limit: int = Query(200, ge=1, le=2000),
    db: AsyncSession = Depends(get_db),
):
    svc = ReportingService(db)
    rows = await svc.inventory_ledger_rows(
        start_date=start_date,
        end_date=end_date,
        source_type=source_type,
        limit=limit,
    )
    return APIResponse(data=rows)


@router.get("/export/daily.xlsx")
async def export_daily_xlsx(
    report_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
):
    """导出日报 Excel"""
    d = report_date or date.today()
    svc = ReportingService(db)
    try:
        content = await svc.export_daily_excel(d)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    filename = f"daily_report_{d.isoformat()}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/ledgers.xlsx")
async def export_ledgers_xlsx(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    source_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """导出库存流水 Excel"""
    svc = ReportingService(db)
    try:
        content = await svc.export_ledger_excel(start_date, end_date, source_type)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    filename = "stock_ledgers.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export/work-orders.xlsx")
async def export_work_orders_xlsx(db: AsyncSession = Depends(get_db)):
    svc = ReportingService(db)
    try:
        content = await svc.export_work_orders_excel()
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="work_orders.xlsx"'},
    )


@router.get("/export/balances.xlsx")
async def export_balances_xlsx(db: AsyncSession = Depends(get_db)):
    svc = ReportingService(db)
    try:
        content = await svc.export_balances_excel()
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="stock_balances.xlsx"'},
    )
