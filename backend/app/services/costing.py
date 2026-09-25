"""成本服务 —— 按工单归集实际材料成本"""
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.costing import MaterialStandardCost, WorkOrderCost
from app.models.inventory import StockLedger, StockSourceType
from app.models.production import WorkOrder, WorkOrderMaterial, WorkOrderOperation
from app.models.purchase import PurchasePriceHistory


class CostingError(Exception):
    pass


class CostingService:
    def __init__(self, db: AsyncSession, operator: str = "system"):
        self.db = db
        self.operator = operator

    async def set_standard_cost(
        self,
        material_id: int,
        unit_cost: Decimal,
        currency: str = "CNY",
        remark: Optional[str] = None,
    ) -> MaterialStandardCost:
        existing = (
            await self.db.execute(
                select(MaterialStandardCost).where(
                    MaterialStandardCost.material_id == material_id
                )
            )
        ).scalar_one_or_none()
        if existing:
            existing.unit_cost = unit_cost
            existing.currency = currency
            existing.remark = remark
            return existing
        obj = MaterialStandardCost(
            material_id=material_id,
            unit_cost=unit_cost,
            currency=currency,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def _unit_cost(self, material_id: int) -> Decimal:
        """优先标准成本，否则最近采购价"""
        std = (
            await self.db.execute(
                select(MaterialStandardCost).where(
                    MaterialStandardCost.material_id == material_id
                )
            )
        ).scalar_one_or_none()
        if std:
            return std.unit_cost

        price = (
            await self.db.execute(
                select(PurchasePriceHistory)
                .where(PurchasePriceHistory.material_id == material_id)
                .order_by(PurchasePriceHistory.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if price:
            return price.unit_price
        return Decimal("0")

    async def calculate_work_order_cost(self, work_order_id: int) -> WorkOrderCost:
        """
        实际材料成本 = Σ (净领料数量 × 单价)
        报废成本简化：按工序报废数量分摊材料（可选，此处用工序 scrap 比例估算）
        """
        wo = await self.db.get(WorkOrder, work_order_id)
        if not wo:
            raise CostingError("工单不存在")

        # 净领料
        mats = (
            await self.db.execute(
                select(WorkOrderMaterial).where(
                    WorkOrderMaterial.work_order_id == work_order_id
                )
            )
        ).scalars().all()

        material_cost = Decimal("0")
        for m in mats:
            net = m.qty_issued - m.qty_returned
            if net <= 0:
                continue
            unit_cost = await self._unit_cost(m.material_id)
            material_cost += net * unit_cost

        # 报废：用工单 scrap_qty 或工序 scrap 合计
        ops = (
            await self.db.execute(
                select(WorkOrderOperation).where(
                    WorkOrderOperation.work_order_id == work_order_id
                )
            )
        ).scalars().all()
        total_scrap = sum((o.qty_scrap for o in ops), Decimal("0"))
        scrap_cost = Decimal("0")
        if wo.completed_qty + total_scrap > 0 and total_scrap > 0:
            # 按报废占比分摊材料成本
            ratio = total_scrap / (wo.completed_qty + total_scrap)
            scrap_cost = (material_cost * ratio).quantize(Decimal("0.0001"))

        # 模具/工序成本首版记 0，预留字段
        mold_cost = Decimal("0")
        process_cost = Decimal("0")

        total = material_cost + mold_cost + process_cost
        completed = wo.completed_qty or Decimal("0")
        unit = (total / completed) if completed > 0 else Decimal("0")

        existing = (
            await self.db.execute(
                select(WorkOrderCost).where(WorkOrderCost.work_order_id == work_order_id)
            )
        ).scalar_one_or_none()

        if existing:
            existing.material_cost = material_cost
            existing.scrap_cost = scrap_cost
            existing.mold_cost = mold_cost
            existing.process_cost = process_cost
            existing.total_cost = total
            existing.completed_qty = completed
            existing.unit_cost = unit
            await self.db.flush()
            return existing

        obj = WorkOrderCost(
            work_order_id=work_order_id,
            material_cost=material_cost,
            scrap_cost=scrap_cost,
            mold_cost=mold_cost,
            process_cost=process_cost,
            total_cost=total,
            completed_qty=completed,
            unit_cost=unit,
            created_by=self.operator,
        )
        self.db.add(obj)
        await self.db.flush()
        return obj
