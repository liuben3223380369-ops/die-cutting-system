"""计划 / MRP API"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.planning import MrpRequirement, MrpRun, SalesOrder, SalesOrderLine
from app.schemas.common import APIResponse
from app.schemas.planning import (
    MrpRunOut,
    MrpRunRequest,
    MrpRequirementOut,
    SalesOrderCreate,
    SalesOrderOut,
    SOLineOut,
)
from app.services.planning import PlanningError, PlanningService

router = APIRouter(prefix="/planning", tags=["计划MRP"])


def _so_out(so: SalesOrder, lines: list) -> SalesOrderOut:
    return SalesOrderOut(
        id=so.id,
        doc_no=so.doc_no,
        status=so.status,
        customer_id=so.customer_id,
        order_date=so.order_date,
        required_date=so.required_date,
        remark=so.remark,
        created_at=so.created_at,
        lines=[SOLineOut.model_validate(l) for l in lines],
    )


@router.post("/sales-orders", response_model=APIResponse[SalesOrderOut])
async def create_sales_order(body: SalesOrderCreate, db: AsyncSession = Depends(get_db)):
    svc = PlanningService(db)
    try:
        so = await svc.create_sales_order(
            customer_id=body.customer_id,
            order_date=body.order_date,
            lines=[l.model_dump() for l in body.lines],
            required_date=body.required_date,
            remark=body.remark,
        )
        lines = (
            await db.execute(
                select(SalesOrderLine).where(SalesOrderLine.order_id == so.id)
            )
        ).scalars().all()
        return APIResponse(data=_so_out(so, lines))
    except PlanningError as e:
        raise HTTPException(400, str(e))


@router.post("/sales-orders/{order_id}/confirm", response_model=APIResponse[SalesOrderOut])
async def confirm_sales_order(order_id: int, db: AsyncSession = Depends(get_db)):
    svc = PlanningService(db)
    try:
        so = await svc.confirm_sales_order(order_id)
        lines = (
            await db.execute(
                select(SalesOrderLine).where(SalesOrderLine.order_id == so.id)
            )
        ).scalars().all()
        return APIResponse(data=_so_out(so, lines))
    except PlanningError as e:
        raise HTTPException(400, str(e))


@router.get("/sales-orders", response_model=APIResponse[List[SalesOrderOut]])
async def list_sales_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SalesOrder).order_by(SalesOrder.id.desc()).limit(50)
    )
    out = []
    for so in result.scalars().all():
        lines = (
            await db.execute(
                select(SalesOrderLine).where(SalesOrderLine.order_id == so.id)
            )
        ).scalars().all()
        out.append(_so_out(so, lines))
    return APIResponse(data=out)


@router.post("/mrp/run", response_model=APIResponse[MrpRunOut])
async def run_mrp(body: MrpRunRequest, db: AsyncSession = Depends(get_db)):
    """执行 MRP，返回运行结果与需求明细"""
    svc = PlanningService(db)
    try:
        run = await svc.run_mrp(
            sales_order_id=body.sales_order_id,
            remark=body.remark,
        )
        reqs = await svc.get_run_requirements(run.id)
        return APIResponse(
            data=MrpRunOut(
                id=run.id,
                run_no=run.run_no,
                status=run.status,
                sales_order_id=run.sales_order_id,
                remark=run.remark,
                created_at=run.created_at,
                requirements=[MrpRequirementOut.model_validate(r) for r in reqs],
            )
        )
    except PlanningError as e:
        raise HTTPException(400, str(e))


@router.get("/mrp/runs", response_model=APIResponse[List[MrpRunOut]])
async def list_mrp_runs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MrpRun).order_by(MrpRun.id.desc()).limit(20))
    out = []
    for run in result.scalars().all():
        reqs = (
            await db.execute(
                select(MrpRequirement)
                .where(MrpRequirement.run_id == run.id)
                .order_by(MrpRequirement.level)
            )
        ).scalars().all()
        out.append(
            MrpRunOut(
                id=run.id,
                run_no=run.run_no,
                status=run.status,
                sales_order_id=run.sales_order_id,
                remark=run.remark,
                created_at=run.created_at,
                requirements=[MrpRequirementOut.model_validate(r) for r in reqs],
            )
        )
    return APIResponse(data=out)


@router.get("/mrp/runs/{run_id}", response_model=APIResponse[MrpRunOut])
async def get_mrp_run(run_id: int, db: AsyncSession = Depends(get_db)):
    run = await db.get(MrpRun, run_id)
    if not run:
        raise HTTPException(404, "MRP 运行不存在")
    reqs = (
        await db.execute(
            select(MrpRequirement)
            .where(MrpRequirement.run_id == run.id)
            .order_by(MrpRequirement.level)
        )
    ).scalars().all()
    return APIResponse(
        data=MrpRunOut(
            id=run.id,
            run_no=run.run_no,
            status=run.status,
            sales_order_id=run.sales_order_id,
            remark=run.remark,
            created_at=run.created_at,
            requirements=[MrpRequirementOut.model_validate(r) for r in reqs],
        )
    )


class CreateWOFromMrpRequest(BaseModel):
    run_id: int
    warehouse_id: Optional[int] = None
    fg_warehouse_id: Optional[int] = None
    wip_warehouse_id: Optional[int] = None


@router.post("/mrp/create-work-orders", response_model=APIResponse[list])
async def create_work_orders_from_mrp(
    body: CreateWOFromMrpRequest,
    db: AsyncSession = Depends(get_db),
):
    """根据 MRP PRODUCE 建议批量生成生产工单"""
    svc = PlanningService(db)
    try:
        wos = await svc.create_work_orders_from_mrp(
            run_id=body.run_id,
            warehouse_id=body.warehouse_id,
            fg_warehouse_id=body.fg_warehouse_id,
            wip_warehouse_id=body.wip_warehouse_id,
        )
        return APIResponse(
            data=[
                {
                    "id": w.id,
                    "doc_no": w.doc_no,
                    "status": w.status,
                    "product_id": w.product_id,
                    "plan_qty": str(w.plan_qty),
                }
                for w in wos
            ]
        )
    except PlanningError as e:
        raise HTTPException(400, str(e))


class CreatePOFromMrpRequest(BaseModel):
    run_id: int
    supplier_id: Optional[int] = None
    auto_confirm: bool = False
    split_by_default_supplier: bool = True


@router.post("/mrp/create-purchase-orders", response_model=APIResponse[list])
async def create_purchase_orders_from_mrp(
    body: CreatePOFromMrpRequest,
    db: AsyncSession = Depends(get_db),
):
    """根据 MRP PURCHASE 建议生成采购订单"""
    from datetime import date as _date
    svc = PlanningService(db)
    try:
        pos = await svc.create_purchase_orders_from_mrp(
            run_id=body.run_id,
            supplier_id=body.supplier_id,
            order_date=_date.today(),
            auto_confirm=body.auto_confirm,
            split_by_default_supplier=body.split_by_default_supplier,
        )
        return APIResponse(
            data=[
                {
                    "id": p.id,
                    "doc_no": p.doc_no,
                    "status": p.status,
                    "supplier_id": p.supplier_id,
                }
                for p in pos
            ]
        )
    except PlanningError as e:
        raise HTTPException(400, str(e))
