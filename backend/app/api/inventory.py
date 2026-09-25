"""库存 API —— 所有库存变化入口"""
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.inventory import StockBalance, StockLedger
from app.schemas.common import APIResponse
from app.schemas.inventory import (
    AdjustRequest,
    StockBalanceOut,
    StockInRequest,
    StockLedgerOut,
    StockOutRequest,
    TransferRequest,
)
from app.services.document_number import generate_document_number
from app.services.inventory import InventoryError, InventoryService, NegativeStockError

router = APIRouter(prefix="/inventory", tags=["库存"])


def _to_balance_out(b: StockBalance) -> StockBalanceOut:
    available = b.qty - b.qty_reserved - b.qty_frozen
    return StockBalanceOut(
        id=b.id,
        material_id=b.material_id,
        warehouse_id=b.warehouse_id,
        location_id=b.location_id,
        batch_no=b.batch_no,
        roll_no=b.roll_no,
        qty=b.qty,
        qty_reserved=b.qty_reserved,
        qty_frozen=b.qty_frozen,
        available_qty=available,
    )


@router.post("/in", response_model=APIResponse[StockLedgerOut])
async def stock_in(body: StockInRequest, db: AsyncSession = Depends(get_db)):
    """统一入库"""
    svc = InventoryService(db)
    try:
        ledger = await svc.stock_in(**body.model_dump())
        await db.refresh(ledger)
        return APIResponse(data=StockLedgerOut.model_validate(ledger))
    except InventoryError as e:
        raise HTTPException(400, str(e))


@router.post("/out", response_model=APIResponse[StockLedgerOut])
async def stock_out(body: StockOutRequest, db: AsyncSession = Depends(get_db)):
    """统一出库"""
    svc = InventoryService(db)
    try:
        ledger = await svc.stock_out(**body.model_dump())
        await db.refresh(ledger)
        return APIResponse(data=StockLedgerOut.model_validate(ledger))
    except NegativeStockError as e:
        raise HTTPException(409, str(e))
    except InventoryError as e:
        raise HTTPException(400, str(e))


@router.post("/adjust", response_model=APIResponse[StockLedgerOut])
async def adjust_stock(body: AdjustRequest, db: AsyncSession = Depends(get_db)):
    """盘点调整（正数盘盈 / 负数盘亏）"""
    svc = InventoryService(db)
    data = body.model_dump()
    source_id = data.pop("source_id") or ""
    try:
        if not source_id:
            source_id = await generate_document_number(db, "ADJ")
        ledger = await svc.adjust(source_id=source_id, **data)
        await db.refresh(ledger)
        return APIResponse(data=StockLedgerOut.model_validate(ledger))
    except NegativeStockError as e:
        raise HTTPException(409, str(e))
    except InventoryError as e:
        raise HTTPException(400, str(e))


@router.post("/transfer", response_model=APIResponse[List[StockLedgerOut]])
async def transfer(body: TransferRequest, db: AsyncSession = Depends(get_db)):
    """库存转移（一出一入）"""
    svc = InventoryService(db)
    try:
        out_l, in_l = await svc.transfer(**body.model_dump())
        await db.refresh(out_l)
        await db.refresh(in_l)
        return APIResponse(
            data=[
                StockLedgerOut.model_validate(out_l),
                StockLedgerOut.model_validate(in_l),
            ]
        )
    except NegativeStockError as e:
        raise HTTPException(409, str(e))
    except InventoryError as e:
        raise HTTPException(400, str(e))


@router.post("/ledgers/{ledger_id}/reverse", response_model=APIResponse[StockLedgerOut])
async def reverse_ledger(
    ledger_id: int,
    reason_code: Optional[str] = None,
    remark: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """冲销流水"""
    svc = InventoryService(db)
    try:
        ledger = await svc.reverse_ledger(
            ledger_id, reason_code=reason_code, remark=remark
        )
        await db.refresh(ledger)
        return APIResponse(data=StockLedgerOut.model_validate(ledger))
    except NegativeStockError as e:
        raise HTTPException(409, str(e))
    except InventoryError as e:
        raise HTTPException(400, str(e))


@router.get("/balances", response_model=APIResponse[List[StockBalanceOut]])
async def list_balances(
    material_id: Optional[int] = None,
    warehouse_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """查询库存余额"""
    stmt = select(StockBalance)
    if material_id:
        stmt = stmt.where(StockBalance.material_id == material_id)
    if warehouse_id:
        stmt = stmt.where(StockBalance.warehouse_id == warehouse_id)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return APIResponse(data=[_to_balance_out(b) for b in items])


@router.get("/ledgers", response_model=APIResponse[List[StockLedgerOut]])
async def list_ledgers(
    material_id: Optional[int] = None,
    source_type: Optional[str] = None,
    source_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """查询库存流水（按时间倒序）"""
    stmt = select(StockLedger).order_by(StockLedger.id.desc()).limit(limit)
    if material_id:
        stmt = stmt.where(StockLedger.material_id == material_id)
    if source_type:
        stmt = stmt.where(StockLedger.source_type == source_type)
    if source_id:
        stmt = stmt.where(StockLedger.source_id == source_id)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return APIResponse(data=[StockLedgerOut.model_validate(i) for i in items])
