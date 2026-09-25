"""库存统一服务 —— 唯一库存事实源入口

所有库存变化必须通过本服务，禁止业务代码直接改 stock_balances.qty。
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import (
    StockBalance,
    StockLedger,
    StockSourceType,
)


class InventoryError(Exception):
    """库存业务异常"""
    pass


class NegativeStockError(InventoryError):
    """负库存拦截"""
    pass


class InventoryService:
    """统一库存服务"""

    def __init__(self, db: AsyncSession, operator: str = "system"):
        self.db = db
        self.operator = operator

    async def _assert_period_open(self) -> None:
        """期间锁定时禁止库存变动（循环依赖用局部导入）"""
        from app.services.period import PeriodError, PeriodService
        try:
            await PeriodService(self.db, self.operator).assert_open()
        except PeriodError as e:
            raise InventoryError(str(e)) from e

    async def _get_or_create_balance(
        self,
        material_id: int,
        warehouse_id: int,
        location_id: Optional[int] = None,
        batch_no: str = "",
        roll_no: str = "",
    ) -> StockBalance:
        """获取或创建余额行（仅内部使用）"""
        stmt = select(StockBalance).where(
            StockBalance.material_id == material_id,
            StockBalance.warehouse_id == warehouse_id,
            StockBalance.location_id == location_id,
            StockBalance.batch_no == (batch_no or ""),
            StockBalance.roll_no == (roll_no or ""),
        )
        result = await self.db.execute(stmt)
        balance = result.scalar_one_or_none()
        if balance is None:
            balance = StockBalance(
                material_id=material_id,
                warehouse_id=warehouse_id,
                location_id=location_id,
                batch_no=batch_no or "",
                roll_no=roll_no or "",
                qty=Decimal("0"),
                qty_reserved=Decimal("0"),
                qty_frozen=Decimal("0"),
            )
            self.db.add(balance)
            await self.db.flush()
        return balance

    async def _write_ledger(
        self,
        *,
        source_type: str,
        source_id: str,
        material_id: int,
        warehouse_id: int,
        qty: Decimal,
        direction: str,
        location_id: Optional[int] = None,
        batch_no: str = "",
        roll_no: str = "",
        unit: str = "PCS",
        source_line_id: Optional[str] = None,
        reason_code: Optional[str] = None,
        remark: Optional[str] = None,
        original_ledger_id: Optional[int] = None,
    ) -> StockLedger:
        """写入流水（内部）"""
        if qty == 0:
            raise InventoryError("流水数量不能为0")

        ledger = StockLedger(
            source_type=source_type,
            source_id=source_id,
            source_line_id=source_line_id,
            material_id=material_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            batch_no=batch_no or "",
            roll_no=roll_no or "",
            qty=qty if direction == "IN" else -abs(qty),
            unit=unit,
            direction=direction,
            original_ledger_id=original_ledger_id,
            reason_code=reason_code,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(ledger)
        await self.db.flush()
        return ledger

    async def stock_in(
        self,
        *,
        source_type: str,
        source_id: str,
        material_id: int,
        warehouse_id: int,
        qty: Decimal,
        location_id: Optional[int] = None,
        batch_no: str = "",
        roll_no: str = "",
        unit: str = "PCS",
        source_line_id: Optional[str] = None,
        reason_code: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> StockLedger:
        """统一入库"""
        if qty <= 0:
            raise InventoryError("入库数量必须大于0")
        await self._assert_period_open()

        balance = await self._get_or_create_balance(
            material_id, warehouse_id, location_id, batch_no, roll_no
        )
        balance.qty += qty

        ledger = await self._write_ledger(
            source_type=source_type,
            source_id=source_id,
            material_id=material_id,
            warehouse_id=warehouse_id,
            qty=qty,
            direction="IN",
            location_id=location_id,
            batch_no=batch_no,
            roll_no=roll_no,
            unit=unit,
            source_line_id=source_line_id,
            reason_code=reason_code,
            remark=remark,
        )
        return ledger

    async def stock_out(
        self,
        *,
        source_type: str,
        source_id: str,
        material_id: int,
        warehouse_id: int,
        qty: Decimal,
        location_id: Optional[int] = None,
        batch_no: str = "",
        roll_no: str = "",
        unit: str = "PCS",
        source_line_id: Optional[str] = None,
        reason_code: Optional[str] = None,
        remark: Optional[str] = None,
        allow_negative: bool = False,
    ) -> StockLedger:
        """统一出库（默认拦截负库存）"""
        if qty <= 0:
            raise InventoryError("出库数量必须大于0")
        await self._assert_period_open()

        balance = await self._get_or_create_balance(
            material_id, warehouse_id, location_id, batch_no, roll_no
        )
        available = balance.qty - balance.qty_reserved - balance.qty_frozen
        if not allow_negative and available < qty:
            raise NegativeStockError(
                f"库存不足：物料{material_id} 仓库{warehouse_id} "
                f"可用{available}，需求{qty}"
            )

        balance.qty -= qty

        ledger = await self._write_ledger(
            source_type=source_type,
            source_id=source_id,
            material_id=material_id,
            warehouse_id=warehouse_id,
            qty=qty,
            direction="OUT",
            location_id=location_id,
            batch_no=batch_no,
            roll_no=roll_no,
            unit=unit,
            source_line_id=source_line_id,
            reason_code=reason_code,
            remark=remark,
        )
        return ledger

    async def transfer(
        self,
        *,
        source_id: str,
        material_id: int,
        from_warehouse_id: int,
        to_warehouse_id: int,
        qty: Decimal,
        from_location_id: Optional[int] = None,
        to_location_id: Optional[int] = None,
        batch_no: str = "",
        roll_no: str = "",
        unit: str = "PCS",
        remark: Optional[str] = None,
    ) -> tuple[StockLedger, StockLedger]:
        """库存转移：一出一入，同一 source_id"""
        out_ledger = await self.stock_out(
            source_type=StockSourceType.TRANSFER,
            source_id=source_id,
            material_id=material_id,
            warehouse_id=from_warehouse_id,
            qty=qty,
            location_id=from_location_id,
            batch_no=batch_no,
            roll_no=roll_no,
            unit=unit,
            remark=remark,
        )
        in_ledger = await self.stock_in(
            source_type=StockSourceType.TRANSFER,
            source_id=source_id,
            material_id=material_id,
            warehouse_id=to_warehouse_id,
            qty=qty,
            location_id=to_location_id,
            batch_no=batch_no,
            roll_no=roll_no,
            unit=unit,
            remark=remark,
        )
        return out_ledger, in_ledger

    async def reverse_ledger(
        self,
        original_ledger_id: int,
        *,
        reason_code: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> StockLedger:
        """冲销某条流水（写反向流水，不删除原流水）"""
        await self._assert_period_open()
        stmt = select(StockLedger).where(StockLedger.id == original_ledger_id)
        result = await self.db.execute(stmt)
        original = result.scalar_one_or_none()
        if original is None:
            raise InventoryError(f"流水不存在: {original_ledger_id}")
        if original.is_reversed:
            raise InventoryError(f"流水已被冲销: {original_ledger_id}")

        # 反向数量
        reverse_qty = abs(original.qty)
        reverse_direction = "OUT" if original.direction == "IN" else "IN"

        balance = await self._get_or_create_balance(
            original.material_id,
            original.warehouse_id,
            original.location_id,
            original.batch_no,
            original.roll_no,
        )
        if reverse_direction == "IN":
            balance.qty += reverse_qty
        else:
            if balance.qty < reverse_qty:
                raise NegativeStockError("冲销后将导致负库存，已拦截")
            balance.qty -= reverse_qty

        ledger = await self._write_ledger(
            source_type=StockSourceType.REVERSAL,
            source_id=f"REV-{original.id}",
            material_id=original.material_id,
            warehouse_id=original.warehouse_id,
            qty=reverse_qty,
            direction=reverse_direction,
            location_id=original.location_id,
            batch_no=original.batch_no,
            roll_no=original.roll_no,
            unit=original.unit,
            reason_code=reason_code,
            remark=remark or f"冲销流水#{original.id}",
            original_ledger_id=original.id,
        )
        original.is_reversed = True
        return ledger


    async def adjust(
        self,
        *,
        material_id: int,
        warehouse_id: int,
        qty_delta: Decimal,
        source_id: str,
        location_id: Optional[int] = None,
        batch_no: str = "",
        roll_no: str = "",
        unit: str = "PCS",
        reason_code: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> StockLedger:
        """盘点调整：qty_delta > 0 盘盈入库，< 0 盘亏出库"""
        if qty_delta == 0:
            raise InventoryError("调整数量不能为0")
        if qty_delta > 0:
            return await self.stock_in(
                source_type=StockSourceType.ADJUST,
                source_id=source_id,
                material_id=material_id,
                warehouse_id=warehouse_id,
                qty=qty_delta,
                location_id=location_id,
                batch_no=batch_no,
                roll_no=roll_no,
                unit=unit,
                reason_code=reason_code,
                remark=remark or "盘点盘盈",
            )
        return await self.stock_out(
            source_type=StockSourceType.ADJUST,
            source_id=source_id,
            material_id=material_id,
            warehouse_id=warehouse_id,
            qty=abs(qty_delta),
            location_id=location_id,
            batch_no=batch_no,
            roll_no=roll_no,
            unit=unit,
            reason_code=reason_code,
            remark=remark or "盘点盘亏",
            allow_negative=False,
        )

    async def get_available_qty(
        self,
        material_id: int,
        warehouse_id: int,
        location_id: Optional[int] = None,
        batch_no: str = "",
        roll_no: str = "",
    ) -> Decimal:
        """查询可用库存"""
        balance = await self._get_or_create_balance(
            material_id, warehouse_id, location_id, batch_no, roll_no
        )
        return balance.qty - balance.qty_reserved - balance.qty_frozen
