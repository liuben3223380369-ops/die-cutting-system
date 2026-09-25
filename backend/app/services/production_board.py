"""生产看板 —— 在制工单总览与简易产能视图"""
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production import WorkOrder, WorkOrderMaterial, WorkOrderOperation


class ProductionBoardService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def board(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """在制/全部工单看板数据"""
        stmt = select(WorkOrder).order_by(WorkOrder.id.desc()).limit(limit)
        if status:
            stmt = stmt.where(WorkOrder.status == status)
        else:
            # 默认在制：排除终态
            stmt = stmt.where(
                WorkOrder.status.in_(
                    ["DRAFT", "RELEASED", "IN_PROGRESS"]
                )
            )
        wos = (await self.db.execute(stmt)).scalars().all()

        cards = []
        for wo in wos:
            ops = (
                await self.db.execute(
                    select(WorkOrderOperation)
                    .where(WorkOrderOperation.work_order_id == wo.id)
                    .order_by(WorkOrderOperation.seq)
                )
            ).scalars().all()
            mats = (
                await self.db.execute(
                    select(WorkOrderMaterial).where(
                        WorkOrderMaterial.work_order_id == wo.id
                    )
                )
            ).scalars().all()

            plan = wo.plan_qty or Decimal("0")
            done = wo.completed_qty or Decimal("0")
            progress = float(min(done / plan * 100, 100)) if plan > 0 else 0.0

            issued = sum((m.qty_issued for m in mats), Decimal("0"))
            required = sum((m.qty_required for m in mats), Decimal("0"))
            material_pct = (
                float(min(issued / required * 100, 100)) if required > 0 else 0.0
            )

            current_op = next(
                (o for o in ops if o.status in ("PENDING", "RUNNING")),
                ops[-1] if ops else None,
            )

            cards.append(
                {
                    "id": wo.id,
                    "doc_no": wo.doc_no,
                    "status": wo.status,
                    "product_id": wo.product_id,
                    "product_version_id": wo.product_version_id,
                    "plan_qty": str(plan),
                    "completed_qty": str(done),
                    "scrap_qty": str(wo.scrap_qty or 0),
                    "progress_pct": round(progress, 1),
                    "material_issue_pct": round(material_pct, 1),
                    "current_step": (
                        {
                            "seq": current_op.seq,
                            "step_name": current_op.step_name,
                            "step_type": current_op.step_type,
                            "status": current_op.status,
                        }
                        if current_op
                        else None
                    ),
                    "ops_done": sum(1 for o in ops if o.status == "DONE"),
                    "ops_total": len(ops),
                    "plan_start": wo.plan_start.isoformat() if wo.plan_start else None,
                    "plan_end": wo.plan_end.isoformat() if wo.plan_end else None,
                }
            )

        # 汇总
        counts = (
            await self.db.execute(
                select(WorkOrder.status, func.count())
                .group_by(WorkOrder.status)
            )
        ).all()
        status_counts = {row[0]: row[1] for row in counts}

        return {
            "summary": {
                "draft": status_counts.get("DRAFT", 0),
                "released": status_counts.get("RELEASED", 0),
                "in_progress": status_counts.get("IN_PROGRESS", 0),
                "completed": status_counts.get("COMPLETED", 0),
                "cancelled": status_counts.get("CANCELLED", 0),
                "active_cards": len(cards),
            },
            "cards": cards,
        }
