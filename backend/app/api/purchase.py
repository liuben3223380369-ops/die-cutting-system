from pydantic import BaseModel
"""采购 API"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.purchase import (
    ArrivalNote,
    ArrivalNoteLine,
    IQCRecord,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchasePriceHistory,
    PurchaseRequest,
    PurchaseRequestLine,
    PurchaseReturn,
    PurchaseReturnLine,
)
from app.schemas.common import APIResponse
from app.schemas.purchase import (
    ArrivalNoteCreate,
    ArrivalNoteOut,
    ArrivalLineOut,
    IQCCreate,
    IQCOut,
    PurchaseOrderCreate,
    PurchaseOrderOut,
    POLineOut,
    PurchaseRequestCreate,
    PurchaseRequestOut,
    PRLineOut,
    PurchaseReturnCreate,
    PurchaseReturnOut,
    ReturnLineOut,
    PriceHistoryOut,
)
from app.services.purchase import PurchaseError, PurchaseService

router = APIRouter(prefix="/purchase", tags=["采购"])


# ---------- 采购申请 ----------
@router.post("/requests", response_model=APIResponse[PurchaseRequestOut])
async def create_request(body: PurchaseRequestCreate, db: AsyncSession = Depends(get_db)):
    svc = PurchaseService(db)
    try:
        pr = await svc.create_request(
            request_date=body.request_date,
            lines=[l.model_dump() for l in body.lines],
            requester=body.requester,
            remark=body.remark,
        )
        lines = (
            await db.execute(
                select(PurchaseRequestLine).where(
                    PurchaseRequestLine.request_id == pr.id
                )
            )
        ).scalars().all()
        out = PurchaseRequestOut(
            id=pr.id,
            doc_no=pr.doc_no,
            status=pr.status,
            request_date=pr.request_date,
            requester=pr.requester,
            remark=pr.remark,
            created_at=pr.created_at,
            lines=[PRLineOut.model_validate(l) for l in lines],
        )
        return APIResponse(data=out)
    except PurchaseError as e:
        raise HTTPException(400, str(e))


@router.post("/requests/{request_id}/submit", response_model=APIResponse[PurchaseRequestOut])
async def submit_request(request_id: int, db: AsyncSession = Depends(get_db)):
    svc = PurchaseService(db)
    try:
        pr = await svc.submit_request(request_id)
        lines = (
            await db.execute(
                select(PurchaseRequestLine).where(
                    PurchaseRequestLine.request_id == pr.id
                )
            )
        ).scalars().all()
        out = PurchaseRequestOut(
            id=pr.id,
            doc_no=pr.doc_no,
            status=pr.status,
            request_date=pr.request_date,
            requester=pr.requester,
            remark=pr.remark,
            created_at=pr.created_at,
            lines=[PRLineOut.model_validate(l) for l in lines],
        )
        return APIResponse(data=out)
    except PurchaseError as e:
        raise HTTPException(400, str(e))


@router.get("/requests", response_model=APIResponse[List[PurchaseRequestOut]])
async def list_requests(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PurchaseRequest).order_by(PurchaseRequest.id.desc()).limit(50)
    )
    items = result.scalars().all()
    out_list = []
    for pr in items:
        lines = (
            await db.execute(
                select(PurchaseRequestLine).where(
                    PurchaseRequestLine.request_id == pr.id
                )
            )
        ).scalars().all()
        out_list.append(
            PurchaseRequestOut(
                id=pr.id,
                doc_no=pr.doc_no,
                status=pr.status,
                request_date=pr.request_date,
                requester=pr.requester,
                remark=pr.remark,
                created_at=pr.created_at,
                lines=[PRLineOut.model_validate(l) for l in lines],
            )
        )
    return APIResponse(data=out_list)


# ---------- 采购订单 ----------


class CreateOrderFromRequestBody(BaseModel):
    request_id: int
    supplier_id: int
    auto_confirm: bool = False


@router.post("/orders/from-request", response_model=APIResponse[PurchaseOrderOut])
async def create_order_from_request(
    body: CreateOrderFromRequestBody, db: AsyncSession = Depends(get_db)
):
    """采购申请转采购订单"""
    svc = PurchaseService(db)
    try:
        po = await svc.create_order_from_request(
            request_id=body.request_id,
            supplier_id=body.supplier_id,
            auto_confirm=body.auto_confirm,
        )
        po = await svc.get_order_with_lines(po.id)
        lines = list(po.lines) if po and hasattr(po, "lines") else []
        # rebuild out similar to get_order
        from app.models.purchase import PurchaseOrderLine
        result = await db.execute(
            select(PurchaseOrderLine).where(PurchaseOrderLine.order_id == po.id)
        )
        lines = result.scalars().all()
        out = PurchaseOrderOut(
            id=po.id,
            doc_no=po.doc_no,
            status=po.status,
            supplier_id=po.supplier_id,
            order_date=po.order_date,
            expected_date=po.expected_date,
            currency=po.currency,
            remark=po.remark,
            request_id=po.request_id,
            created_at=po.created_at,
            lines=[POLineOut.model_validate(l) for l in lines],
        )
        return APIResponse(data=out)
    except PurchaseError as e:
        raise HTTPException(400, str(e))


@router.post("/orders", response_model=APIResponse[PurchaseOrderOut])
async def create_order(body: PurchaseOrderCreate, db: AsyncSession = Depends(get_db)):
    svc = PurchaseService(db)
    try:
        po = await svc.create_order(
            supplier_id=body.supplier_id,
            order_date=body.order_date,
            lines=[l.model_dump() for l in body.lines],
            expected_date=body.expected_date,
            currency=body.currency,
            remark=body.remark,
            request_id=body.request_id,
        )
        lines = (
            await db.execute(
                select(PurchaseOrderLine).where(PurchaseOrderLine.order_id == po.id)
            )
        ).scalars().all()
        out = PurchaseOrderOut(
            id=po.id,
            doc_no=po.doc_no,
            status=po.status,
            supplier_id=po.supplier_id,
            order_date=po.order_date,
            expected_date=po.expected_date,
            currency=po.currency,
            remark=po.remark,
            request_id=po.request_id,
            created_at=po.created_at,
            lines=[POLineOut.model_validate(l) for l in lines],
        )
        return APIResponse(data=out)
    except PurchaseError as e:
        raise HTTPException(400, str(e))


@router.post("/orders/{order_id}/confirm", response_model=APIResponse[PurchaseOrderOut])
async def confirm_order(order_id: int, db: AsyncSession = Depends(get_db)):
    svc = PurchaseService(db)
    try:
        po = await svc.confirm_order(order_id)
        lines = (
            await db.execute(
                select(PurchaseOrderLine).where(PurchaseOrderLine.order_id == po.id)
            )
        ).scalars().all()
        out = PurchaseOrderOut(
            id=po.id,
            doc_no=po.doc_no,
            status=po.status,
            supplier_id=po.supplier_id,
            order_date=po.order_date,
            expected_date=po.expected_date,
            currency=po.currency,
            remark=po.remark,
            request_id=po.request_id,
            created_at=po.created_at,
            lines=[POLineOut.model_validate(l) for l in lines],
        )
        return APIResponse(data=out)
    except PurchaseError as e:
        raise HTTPException(400, str(e))


@router.get("/orders", response_model=APIResponse[List[PurchaseOrderOut]])
async def list_orders(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PurchaseOrder).order_by(PurchaseOrder.id.desc()).limit(50)
    )
    items = result.scalars().all()
    out_list = []
    for po in items:
        lines = (
            await db.execute(
                select(PurchaseOrderLine).where(PurchaseOrderLine.order_id == po.id)
            )
        ).scalars().all()
        out_list.append(
            PurchaseOrderOut(
                id=po.id,
                doc_no=po.doc_no,
                status=po.status,
                supplier_id=po.supplier_id,
                order_date=po.order_date,
                expected_date=po.expected_date,
                currency=po.currency,
                remark=po.remark,
                request_id=po.request_id,
                created_at=po.created_at,
                lines=[POLineOut.model_validate(l) for l in lines],
            )
        )
    return APIResponse(data=out_list)


@router.get("/orders/{order_id}", response_model=APIResponse[PurchaseOrderOut])
async def get_order(order_id: int, db: AsyncSession = Depends(get_db)):
    po = await db.get(PurchaseOrder, order_id)
    if not po:
        raise HTTPException(404, "订单不存在")
    lines = (
        await db.execute(
            select(PurchaseOrderLine).where(PurchaseOrderLine.order_id == po.id)
        )
    ).scalars().all()
    out = PurchaseOrderOut(
        id=po.id,
        doc_no=po.doc_no,
        status=po.status,
        supplier_id=po.supplier_id,
        order_date=po.order_date,
        expected_date=po.expected_date,
        currency=po.currency,
        remark=po.remark,
        request_id=po.request_id,
        created_at=po.created_at,
        lines=[POLineOut.model_validate(l) for l in lines],
    )
    return APIResponse(data=out)


# ---------- 到货 ----------
@router.post("/arrivals", response_model=APIResponse[ArrivalNoteOut])
async def create_arrival(body: ArrivalNoteCreate, db: AsyncSession = Depends(get_db)):
    svc = PurchaseService(db)
    try:
        note = await svc.create_arrival(
            order_id=body.order_id,
            arrival_date=body.arrival_date,
            warehouse_id=body.warehouse_id,
            lines=[l.model_dump() for l in body.lines],
            remark=body.remark,
        )
        lines = (
            await db.execute(
                select(ArrivalNoteLine).where(ArrivalNoteLine.arrival_id == note.id)
            )
        ).scalars().all()
        out = ArrivalNoteOut(
            id=note.id,
            doc_no=note.doc_no,
            status=note.status,
            order_id=note.order_id,
            supplier_id=note.supplier_id,
            arrival_date=note.arrival_date,
            warehouse_id=note.warehouse_id,
            remark=note.remark,
            created_at=note.created_at,
            lines=[ArrivalLineOut.model_validate(l) for l in lines],
        )
        return APIResponse(data=out)
    except PurchaseError as e:
        raise HTTPException(400, str(e))


@router.get("/arrivals", response_model=APIResponse[List[ArrivalNoteOut]])
async def list_arrivals(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ArrivalNote).order_by(ArrivalNote.id.desc()).limit(50)
    )
    items = result.scalars().all()
    out_list = []
    for note in items:
        lines = (
            await db.execute(
                select(ArrivalNoteLine).where(ArrivalNoteLine.arrival_id == note.id)
            )
        ).scalars().all()
        out_list.append(
            ArrivalNoteOut(
                id=note.id,
                doc_no=note.doc_no,
                status=note.status,
                order_id=note.order_id,
                supplier_id=note.supplier_id,
                arrival_date=note.arrival_date,
                warehouse_id=note.warehouse_id,
                remark=note.remark,
                created_at=note.created_at,
                lines=[ArrivalLineOut.model_validate(l) for l in lines],
            )
        )
    return APIResponse(data=out_list)


# ---------- IQC ----------
@router.post("/iqc", response_model=APIResponse[IQCOut])
async def do_iqc(body: IQCCreate, db: AsyncSession = Depends(get_db)):
    """IQC 检验 → 合格入库 / 不合格隔离"""
    svc = PurchaseService(db)
    try:
        iqc = await svc.do_iqc(
            arrival_line_id=body.arrival_line_id,
            result=body.result,
            qty_inspected=body.qty_inspected,
            qty_passed=body.qty_passed,
            qty_failed=body.qty_failed,
            inspect_date=body.inspect_date,
            inspector=body.inspector,
            defect_codes=body.defect_codes,
            remark=body.remark,
            target_warehouse_id=body.target_warehouse_id,
            hold_warehouse_id=body.hold_warehouse_id,
        )
        return APIResponse(data=IQCOut.model_validate(iqc))
    except PurchaseError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        # InventoryError 等
        raise HTTPException(400, str(e))


@router.get("/iqc", response_model=APIResponse[List[IQCOut]])
async def list_iqc(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(IQCRecord).order_by(IQCRecord.id.desc()).limit(50)
    )
    items = result.scalars().all()
    return APIResponse(data=[IQCOut.model_validate(i) for i in items])


# ---------- 采购退货 ----------
@router.post("/returns", response_model=APIResponse[PurchaseReturnOut])
async def create_return(body: PurchaseReturnCreate, db: AsyncSession = Depends(get_db)):
    svc = PurchaseService(db)
    try:
        ret = await svc.create_return(
            supplier_id=body.supplier_id,
            return_date=body.return_date,
            warehouse_id=body.warehouse_id,
            lines=[l.model_dump() for l in body.lines],
            order_id=body.order_id,
            reason_code=body.reason_code,
            remark=body.remark,
        )
        lines = (
            await db.execute(
                select(PurchaseReturnLine).where(PurchaseReturnLine.return_id == ret.id)
            )
        ).scalars().all()
        out = PurchaseReturnOut(
            id=ret.id,
            doc_no=ret.doc_no,
            status=ret.status,
            supplier_id=ret.supplier_id,
            order_id=ret.order_id,
            return_date=ret.return_date,
            warehouse_id=ret.warehouse_id,
            reason_code=ret.reason_code,
            remark=ret.remark,
            created_at=ret.created_at,
            lines=[ReturnLineOut.model_validate(l) for l in lines],
        )
        return APIResponse(data=out)
    except PurchaseError as e:
        raise HTTPException(400, str(e))


@router.post("/returns/{return_id}/confirm", response_model=APIResponse[PurchaseReturnOut])
async def confirm_return(return_id: int, db: AsyncSession = Depends(get_db)):
    """确认退货 → 出库 (PURCHASE_RETURN)"""
    svc = PurchaseService(db)
    try:
        ret = await svc.confirm_return(return_id)
        lines = (
            await db.execute(
                select(PurchaseReturnLine).where(PurchaseReturnLine.return_id == ret.id)
            )
        ).scalars().all()
        out = PurchaseReturnOut(
            id=ret.id,
            doc_no=ret.doc_no,
            status=ret.status,
            supplier_id=ret.supplier_id,
            order_id=ret.order_id,
            return_date=ret.return_date,
            warehouse_id=ret.warehouse_id,
            reason_code=ret.reason_code,
            remark=ret.remark,
            created_at=ret.created_at,
            lines=[ReturnLineOut.model_validate(l) for l in lines],
        )
        return APIResponse(data=out)
    except PurchaseError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(400, str(e))


@router.get("/returns", response_model=APIResponse[List[PurchaseReturnOut]])
async def list_returns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PurchaseReturn).order_by(PurchaseReturn.id.desc()).limit(50)
    )
    items = result.scalars().all()
    out_list = []
    for ret in items:
        lines = (
            await db.execute(
                select(PurchaseReturnLine).where(PurchaseReturnLine.return_id == ret.id)
            )
        ).scalars().all()
        out_list.append(
            PurchaseReturnOut(
                id=ret.id,
                doc_no=ret.doc_no,
                status=ret.status,
                supplier_id=ret.supplier_id,
                order_id=ret.order_id,
                return_date=ret.return_date,
                warehouse_id=ret.warehouse_id,
                reason_code=ret.reason_code,
                remark=ret.remark,
                created_at=ret.created_at,
                lines=[ReturnLineOut.model_validate(l) for l in lines],
            )
        )
    return APIResponse(data=out_list)


# ---------- 价格历史 ----------
@router.get("/price-history", response_model=APIResponse[List[PriceHistoryOut]])
async def list_price_history(
    supplier_id: Optional[int] = None,
    material_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PurchasePriceHistory).order_by(PurchasePriceHistory.id.desc()).limit(100)
    if supplier_id:
        stmt = stmt.where(PurchasePriceHistory.supplier_id == supplier_id)
    if material_id:
        stmt = stmt.where(PurchasePriceHistory.material_id == material_id)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return APIResponse(data=[PriceHistoryOut.model_validate(i) for i in items])
