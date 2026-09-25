"""生产 API"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.production import (
    OperationReport,
    WorkOrder,
    WorkOrderMaterial,
    WorkOrderOperation,
)
from app.schemas.common import APIResponse
from app.schemas.production import (
    CompleteRequest,
    IssueMaterialsRequest,
    OperationReportOut,
    ReceiveFGRequest,
    ReportOperationRequest,
    ReturnMaterialsRequest,
    WOMaterialOut,
    WOOperationOut,
    WorkOrderCreate,
    WorkOrderOut,
)
from app.services.production import ProductionService as _PS
from app.services.production import ProductionError, ProductionService

router = APIRouter(prefix="/production", tags=["生产"])


async def _wo_out(db: AsyncSession, wo: WorkOrder) -> WorkOrderOut:
    mats = (
        await db.execute(
            select(WorkOrderMaterial).where(WorkOrderMaterial.work_order_id == wo.id)
        )
    ).scalars().all()
    ops = (
        await db.execute(
            select(WorkOrderOperation)
            .where(WorkOrderOperation.work_order_id == wo.id)
            .order_by(WorkOrderOperation.seq)
        )
    ).scalars().all()
    return WorkOrderOut(
        id=wo.id,
        doc_no=wo.doc_no,
        status=wo.status,
        product_id=wo.product_id,
        product_version_id=wo.product_version_id,
        bom_id=wo.bom_id,
        route_id=wo.route_id,
        nesting_id=wo.nesting_id,
        plan_qty=wo.plan_qty,
        completed_qty=wo.completed_qty,
        scrap_qty=wo.scrap_qty,
        unit=wo.unit,
        warehouse_id=wo.warehouse_id,
        fg_warehouse_id=wo.fg_warehouse_id,
        wip_warehouse_id=wo.wip_warehouse_id,
        plan_start=wo.plan_start,
        plan_end=wo.plan_end,
        sales_order_id=wo.sales_order_id,
        remark=wo.remark,
        created_at=wo.created_at,
        materials=[WOMaterialOut.model_validate(m) for m in mats],
        operations=[WOOperationOut.model_validate(o) for o in ops],
        progress_pct=_PS.progress_pct(wo.plan_qty, wo.completed_qty),
    )


@router.post("/work-orders", response_model=APIResponse[WorkOrderOut])
async def create_work_order(body: WorkOrderCreate, db: AsyncSession = Depends(get_db)):
    svc = ProductionService(db)
    try:
        wo = await svc.create_work_order(**body.model_dump())
        return APIResponse(data=await _wo_out(db, wo))
    except ProductionError as e:
        raise HTTPException(400, str(e))


@router.get("/work-orders", response_model=APIResponse[List[WorkOrderOut]])
async def list_work_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WorkOrder).order_by(WorkOrder.id.desc()).limit(50))
    out = []
    for wo in result.scalars().all():
        out.append(await _wo_out(db, wo))
    return APIResponse(data=out)


@router.get("/work-orders/{wo_id}", response_model=APIResponse[WorkOrderOut])
async def get_work_order(wo_id: int, db: AsyncSession = Depends(get_db)):
    wo = await db.get(WorkOrder, wo_id)
    if not wo:
        raise HTTPException(404, "工单不存在")
    return APIResponse(data=await _wo_out(db, wo))


@router.post("/work-orders/{wo_id}/release", response_model=APIResponse[WorkOrderOut])
async def release_work_order(wo_id: int, db: AsyncSession = Depends(get_db)):
    svc = ProductionService(db)
    try:
        wo = await svc.release_work_order(wo_id)
        return APIResponse(data=await _wo_out(db, wo))
    except ProductionError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/issue", response_model=APIResponse[WorkOrderOut])
async def issue_materials(
    wo_id: int, body: IssueMaterialsRequest, db: AsyncSession = Depends(get_db)
):
    svc = ProductionService(db)
    try:
        wo = await svc.issue_materials(
            wo_id,
            issues=[i.model_dump() for i in body.items],
            warehouse_id=body.warehouse_id,
        )
        return APIResponse(data=await _wo_out(db, wo))
    except ProductionError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/report", response_model=APIResponse[OperationReportOut])
async def report_operation(
    wo_id: int, body: ReportOperationRequest, db: AsyncSession = Depends(get_db)
):
    svc = ProductionService(db)
    try:
        report = await svc.report_operation(
            wo_id=wo_id,
            operation_id=body.operation_id,
            qty_good=body.qty_good,
            qty_reject=body.qty_reject,
            qty_scrap=body.qty_scrap,
            report_date=body.report_date,
            operator_name=body.operator_name,
            downtime_min=body.downtime_min,
            remark=body.remark,
        )
        return APIResponse(data=OperationReportOut.model_validate(report))
    except ProductionError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/return", response_model=APIResponse[WorkOrderOut])
async def return_materials(
    wo_id: int, body: ReturnMaterialsRequest, db: AsyncSession = Depends(get_db)
):
    svc = ProductionService(db)
    try:
        wo = await svc.return_materials(
            wo_id,
            returns=[i.model_dump() for i in body.items],
            warehouse_id=body.warehouse_id,
        )
        return APIResponse(data=await _wo_out(db, wo))
    except ProductionError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/receive-fg", response_model=APIResponse[WorkOrderOut])
async def receive_fg(
    wo_id: int, body: ReceiveFGRequest, db: AsyncSession = Depends(get_db)
):
    svc = ProductionService(db)
    try:
        wo = await svc.receive_fg(
            wo_id=wo_id,
            qty=body.qty,
            warehouse_id=body.warehouse_id,
            material_id=body.material_id,
            batch_no=body.batch_no,
        )
        return APIResponse(data=await _wo_out(db, wo))
    except ProductionError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/complete", response_model=APIResponse[WorkOrderOut])
async def complete_work_order(
    wo_id: int,
    body: CompleteRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    svc = ProductionService(db)
    try:
        force = body.force if body else False
        wo = await svc.complete_work_order(wo_id, force=force)
        return APIResponse(data=await _wo_out(db, wo))
    except ProductionError as e:
        raise HTTPException(400, str(e))


@router.post("/work-orders/{wo_id}/cancel", response_model=APIResponse[WorkOrderOut])
async def cancel_work_order(wo_id: int, db: AsyncSession = Depends(get_db)):
    svc = ProductionService(db)
    try:
        wo = await svc.cancel_work_order(wo_id)
        return APIResponse(data=await _wo_out(db, wo))
    except ProductionError as e:
        raise HTTPException(400, str(e))
