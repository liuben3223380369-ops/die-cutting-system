"""生产服务

工单创建 → 锁定版本/BOM/工艺 → 下达 → 领料 → 报工 → 成品入库 → 完工
"""
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engineering import (
    BomHeader,
    BomLine,
    NestingLayout,
    ProcessRoute,
    ProcessStep,
    ProductVersion,
)
from app.models.inventory import StockSourceType
from app.models.production import (
    OperationReport,
    WorkOrder,
    WorkOrderMaterial,
    WorkOrderOperation,
)
from app.services.document_number import generate_document_number
from app.services.inventory import InventoryService


class ProductionError(Exception):
    pass


class ProductionService:
    def __init__(self, db: AsyncSession, operator: str = "system"):
        self.db = db
        self.operator = operator
        self.inv = InventoryService(db, operator)

    async def create_work_order(
        self,
        product_id: int,
        product_version_id: int,
        plan_qty: Decimal,
        warehouse_id: Optional[int] = None,
        fg_warehouse_id: Optional[int] = None,
        wip_warehouse_id: Optional[int] = None,
        plan_start: Optional[date] = None,
        plan_end: Optional[date] = None,
        sales_order_id: Optional[int] = None,
        unit: str = "PCS",
        remark: Optional[str] = None,
    ) -> WorkOrder:
        """创建工单并锁定 BOM / 工艺 / 排版"""
        version = await self.db.get(ProductVersion, product_version_id)
        if not version:
            raise ProductionError("产品版本不存在")
        if version.status != "RELEASED":
            raise ProductionError("只能对已发布版本创建工单")
        if version.product_id != product_id:
            raise ProductionError("产品与版本不匹配")

        bom = (
            await self.db.execute(
                select(BomHeader).where(
                    BomHeader.product_version_id == product_version_id
                )
            )
        ).scalar_one_or_none()
        route = (
            await self.db.execute(
                select(ProcessRoute).where(
                    ProcessRoute.product_version_id == product_version_id
                )
            )
        ).scalar_one_or_none()
        nesting = (
            await self.db.execute(
                select(NestingLayout)
                .where(
                    NestingLayout.product_version_id == product_version_id,
                    NestingLayout.is_default == True,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if not nesting:
            nesting = (
                await self.db.execute(
                    select(NestingLayout)
                    .where(NestingLayout.product_version_id == product_version_id)
                    .limit(1)
                )
            ).scalar_one_or_none()

        if not bom:
            raise ProductionError("版本无 BOM，无法建工单")
        if not route:
            raise ProductionError("版本无工艺路线，无法建工单")

        doc_no = await generate_document_number(self.db, "WO")
        wo = WorkOrder(
            doc_no=doc_no,
            status="DRAFT",
            product_id=product_id,
            product_version_id=product_version_id,
            bom_id=bom.id,
            route_id=route.id,
            nesting_id=nesting.id if nesting else None,
            plan_qty=plan_qty,
            completed_qty=Decimal("0"),
            scrap_qty=Decimal("0"),
            unit=unit,
            warehouse_id=warehouse_id,
            fg_warehouse_id=fg_warehouse_id,
            wip_warehouse_id=wip_warehouse_id,
            plan_start=plan_start,
            plan_end=plan_end,
            sales_order_id=sales_order_id,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(wo)
        await self.db.flush()

        # 锁定物料需求（BOM × 计划量 × (1+损耗)）
        bom_lines = (
            await self.db.execute(
                select(BomLine).where(
                    BomLine.bom_id == bom.id,
                    BomLine.is_alternative == False,
                )
            )
        ).scalars().all()
        for bl in bom_lines:
            req_qty = plan_qty * bl.qty_per * (Decimal("1") + (bl.scrap_rate or Decimal("0")))
            wom = WorkOrderMaterial(
                work_order_id=wo.id,
                material_id=bl.material_id,
                qty_required=req_qty,
                qty_issued=Decimal("0"),
                qty_returned=Decimal("0"),
                unit=bl.unit,
                created_by=self.operator,
            )
            self.db.add(wom)

        # 锁定工序
        steps = (
            await self.db.execute(
                select(ProcessStep)
                .where(ProcessStep.route_id == route.id)
                .order_by(ProcessStep.seq)
            )
        ).scalars().all()
        for st in steps:
            op = WorkOrderOperation(
                work_order_id=wo.id,
                seq=st.seq,
                step_code=st.step_code,
                step_name=st.step_name,
                step_type=st.step_type,
                mold_id=st.mold_id,
                status="PENDING",
                created_by=self.operator,
            )
            self.db.add(op)

        await self.db.flush()
        return wo

    async def release_work_order(self, wo_id: int) -> WorkOrder:
        wo = await self.db.get(WorkOrder, wo_id)
        if not wo:
            raise ProductionError("工单不存在")
        if wo.status != "DRAFT":
            raise ProductionError(f"当前状态不可下达: {wo.status}")
        wo.status = "RELEASED"
        return wo

    async def issue_materials(
        self,
        wo_id: int,
        issues: list[dict],
        warehouse_id: Optional[int] = None,
    ) -> WorkOrder:
        """
        生产领料。
        issues: [{material_id, qty, batch_no?, roll_no?}]
        """
        wo = await self.db.get(WorkOrder, wo_id)
        if not wo:
            raise ProductionError("工单不存在")
        if wo.status not in ("RELEASED", "IN_PROGRESS"):
            raise ProductionError(f"当前状态不可领料: {wo.status}")

        wh = warehouse_id or wo.warehouse_id
        if not wh:
            raise ProductionError("未指定领料仓库")

        mats = (
            await self.db.execute(
                select(WorkOrderMaterial).where(WorkOrderMaterial.work_order_id == wo_id)
            )
        ).scalars().all()
        mat_map = {m.material_id: m for m in mats}

        for item in issues:
            mid = item["material_id"]
            qty = Decimal(str(item["qty"]))
            if mid not in mat_map:
                raise ProductionError(f"物料 {mid} 不在工单需求中")
            wom = mat_map[mid]
            remain = wom.qty_required - wom.qty_issued + wom.qty_returned
            if qty > remain + Decimal("0.0001"):
                raise ProductionError(
                    f"领料超过需求：物料{mid} 剩余需求{remain}，申请{qty}"
                )

            await self.inv.stock_out(
                source_type=StockSourceType.PRODUCTION_ISSUE,
                source_id=wo.doc_no,
                source_line_id=str(wom.id),
                material_id=mid,
                warehouse_id=wh,
                qty=qty,
                batch_no=item.get("batch_no", ""),
                roll_no=item.get("roll_no", ""),
                unit=wom.unit,
                remark=f"生产领料 {wo.doc_no}",
            )
            # 若配置了 WIP 仓，同步转入在制品仓
            if wo.wip_warehouse_id and wo.wip_warehouse_id != wh:
                await self.inv.stock_in(
                    source_type=StockSourceType.TRANSFER,
                    source_id=wo.doc_no,
                    source_line_id=str(wom.id),
                    material_id=mid,
                    warehouse_id=wo.wip_warehouse_id,
                    qty=qty,
                    batch_no=item.get("batch_no", ""),
                    roll_no=item.get("roll_no", ""),
                    unit=wom.unit,
                    remark=f"领料入WIP {wo.doc_no}",
                )
            wom.qty_issued += qty

        if wo.status == "RELEASED":
            wo.status = "IN_PROGRESS"
        return wo

    async def return_materials(
        self,
        wo_id: int,
        returns: list[dict],
        warehouse_id: Optional[int] = None,
    ) -> WorkOrder:
        """生产退料"""
        wo = await self.db.get(WorkOrder, wo_id)
        if not wo:
            raise ProductionError("工单不存在")
        if wo.status not in ("IN_PROGRESS", "RELEASED"):
            raise ProductionError(f"当前状态不可退料: {wo.status}")

        wh = warehouse_id or wo.warehouse_id
        if not wh:
            raise ProductionError("未指定仓库")

        mats = (
            await self.db.execute(
                select(WorkOrderMaterial).where(WorkOrderMaterial.work_order_id == wo_id)
            )
        ).scalars().all()
        mat_map = {m.material_id: m for m in mats}

        for item in returns:
            mid = item["material_id"]
            qty = Decimal(str(item["qty"]))
            if mid not in mat_map:
                raise ProductionError(f"物料 {mid} 不在工单需求中")
            wom = mat_map[mid]
            net_issued = wom.qty_issued - wom.qty_returned
            if qty > net_issued:
                raise ProductionError(f"退料超过已领：物料{mid}")

            if wo.wip_warehouse_id and wo.wip_warehouse_id != wh:
                await self.inv.stock_out(
                    source_type=StockSourceType.TRANSFER,
                    source_id=wo.doc_no,
                    source_line_id=str(wom.id),
                    material_id=mid,
                    warehouse_id=wo.wip_warehouse_id,
                    qty=qty,
                    batch_no=item.get("batch_no", ""),
                    roll_no=item.get("roll_no", ""),
                    unit=wom.unit,
                    remark=f"WIP退回 {wo.doc_no}",
                    allow_negative=False,
                )
            await self.inv.stock_in(
                source_type=StockSourceType.PRODUCTION_RETURN,
                source_id=wo.doc_no,
                source_line_id=str(wom.id),
                material_id=mid,
                warehouse_id=wh,
                qty=qty,
                batch_no=item.get("batch_no", ""),
                roll_no=item.get("roll_no", ""),
                unit=wom.unit,
                remark=f"生产退料 {wo.doc_no}",
            )
            wom.qty_returned += qty

        return wo

    async def report_operation(
        self,
        wo_id: int,
        operation_id: int,
        qty_good: Decimal,
        qty_reject: Decimal = Decimal("0"),
        qty_scrap: Decimal = Decimal("0"),
        report_date: Optional[date] = None,
        operator_name: Optional[str] = None,
        downtime_min: Optional[Decimal] = None,
        remark: Optional[str] = None,
        enforce_sequence: bool = True,
    ) -> OperationReport:
        """工序报工（默认强制顺序：前序须有报工）"""
        wo = await self.db.get(WorkOrder, wo_id)
        if not wo:
            raise ProductionError("工单不存在")
        if wo.status not in ("RELEASED", "IN_PROGRESS"):
            raise ProductionError(f"当前状态不可报工: {wo.status}")

        op = await self.db.get(WorkOrderOperation, operation_id)
        if not op or op.work_order_id != wo_id:
            raise ProductionError("工序不存在或不属于该工单")

        if qty_good < 0 or qty_reject < 0 or qty_scrap < 0:
            raise ProductionError("报工数量不能为负")
        if qty_good + qty_reject + qty_scrap <= 0:
            raise ProductionError("报工数量合计必须大于0")

        # 工序顺序：前序至少有一次报工（qty_good+reject+scrap > 0）
        if enforce_sequence:
            prev_ops = (
                await self.db.execute(
                    select(WorkOrderOperation)
                    .where(
                        WorkOrderOperation.work_order_id == wo_id,
                        WorkOrderOperation.seq < op.seq,
                    )
                    .order_by(WorkOrderOperation.seq)
                )
            ).scalars().all()
            for prev in prev_ops:
                done_qty = prev.qty_good + prev.qty_reject + prev.qty_scrap
                if done_qty <= 0 and prev.status == "PENDING":
                    raise ProductionError(
                        f"请先完成前序工序「{prev.step_name}」(seq={prev.seq})"
                    )

        # 建议：首道工序报工前至少有领料
        first_op = (
            await self.db.execute(
                select(WorkOrderOperation)
                .where(WorkOrderOperation.work_order_id == wo_id)
                .order_by(WorkOrderOperation.seq)
                .limit(1)
            )
        ).scalar_one_or_none()
        if first_op and first_op.id == op.id:
            mats = (
                await self.db.execute(
                    select(WorkOrderMaterial).where(
                        WorkOrderMaterial.work_order_id == wo_id
                    )
                )
            ).scalars().all()
            if mats and all(m.qty_issued <= 0 for m in mats):
                raise ProductionError("首道工序报工前请先领料")

        doc_no = await generate_document_number(self.db, "OPR")
        report = OperationReport(
            doc_no=doc_no,
            work_order_id=wo_id,
            operation_id=operation_id,
            qty_good=qty_good,
            qty_reject=qty_reject,
            qty_scrap=qty_scrap,
            report_date=report_date or date.today(),
            operator_name=operator_name or self.operator,
            downtime_min=downtime_min,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(report)

        op.qty_good += qty_good
        op.qty_reject += qty_reject
        op.qty_scrap += qty_scrap
        total = op.qty_good + op.qty_reject + op.qty_scrap
        # 累计达到计划量则标记工序完成
        if total >= wo.plan_qty:
            op.status = "DONE"
        else:
            op.status = "RUNNING"

        wo.scrap_qty = (wo.scrap_qty or Decimal("0")) + qty_scrap
        if wo.status == "RELEASED":
            wo.status = "IN_PROGRESS"

        if op.mold_id and (qty_good + qty_reject + qty_scrap) > 0:
            from app.services.engineering import EngineeringService
            eng = EngineeringService(self.db, self.operator)
            hits = int(qty_good + qty_reject + qty_scrap)
            try:
                await eng.add_mold_usage(op.mold_id, hits)
            except Exception:
                pass

        await self.db.flush()
        return report

    async def receive_fg(
        self,
        wo_id: int,
        qty: Decimal,
        warehouse_id: Optional[int] = None,
        material_id: Optional[int] = None,
        batch_no: str = "",
    ) -> WorkOrder:
        """成品/半成品入库"""
        wo = await self.db.get(WorkOrder, wo_id)
        if not wo:
            raise ProductionError("工单不存在")
        if wo.status not in ("IN_PROGRESS", "RELEASED"):
            raise ProductionError(f"当前状态不可入库: {wo.status}")

        wh = warehouse_id or wo.fg_warehouse_id
        if not wh:
            raise ProductionError("未指定成品仓库")

        # 成品物料：优先参数，否则取 product.material_id
        mid = material_id
        if not mid:
            from app.models.engineering import Product
            product = await self.db.get(Product, wo.product_id)
            mid = product.material_id if product else None
        if not mid:
            raise ProductionError("未指定成品物料，请在产品档案关联 material_id")

        remain = wo.plan_qty - wo.completed_qty
        if qty > remain + Decimal("0.0001"):
            raise ProductionError(f"入库数量超过剩余计划：剩余{remain}")

        await self.inv.stock_in(
            source_type=StockSourceType.PRODUCTION_IN,
            source_id=wo.doc_no,
            material_id=mid,
            warehouse_id=wh,
            qty=qty,
            batch_no=batch_no,
            unit=wo.unit,
            remark=f"生产入库 {wo.doc_no}",
        )
        wo.completed_qty += qty
        if wo.status == "RELEASED":
            wo.status = "IN_PROGRESS"
        return wo

    async def complete_work_order(
        self,
        wo_id: int,
        force: bool = False,
    ) -> WorkOrder:
        """工单完工

        默认要求：已有成品入库；未强制时检查工序是否均已报工。
        """
        wo = await self.db.get(WorkOrder, wo_id)
        if not wo:
            raise ProductionError("工单不存在")
        if wo.status not in ("IN_PROGRESS", "RELEASED"):
            raise ProductionError(f"当前状态不可完工: {wo.status}")
        if wo.completed_qty <= 0 and not force:
            raise ProductionError("尚无成品入库，无法完工（可 force=true 强制）")

        ops = (
            await self.db.execute(
                select(WorkOrderOperation).where(
                    WorkOrderOperation.work_order_id == wo_id
                )
            )
        ).scalars().all()

        if not force:
            pending = [o for o in ops if o.status == "PENDING"]
            if pending:
                names = "、".join(o.step_name for o in pending[:3])
                raise ProductionError(
                    f"仍有未报工工序：{names}（可 force=true 强制完工）"
                )

        for op in ops:
            op.status = "DONE"

        # 完工时清空 WIP 仓中本工单净领用料（若配置了 WIP）
        if wo.wip_warehouse_id:
            mats = (
                await self.db.execute(
                    select(WorkOrderMaterial).where(
                        WorkOrderMaterial.work_order_id == wo_id
                    )
                )
            ).scalars().all()
            for m in mats:
                net = m.qty_issued - m.qty_returned
                if net > 0:
                    try:
                        await self.inv.stock_out(
                            source_type=StockSourceType.PRODUCTION_ISSUE,
                            source_id=wo.doc_no,
                            source_line_id=str(m.id),
                            material_id=m.material_id,
                            warehouse_id=wo.wip_warehouse_id,
                            qty=net,
                            unit=m.unit,
                            remark=f"完工消耗WIP {wo.doc_no}",
                            allow_negative=True,
                        )
                    except Exception:
                        pass

        wo.status = "COMPLETED"
        return wo

    async def cancel_work_order(self, wo_id: int) -> WorkOrder:
        """取消工单（仅 DRAFT / RELEASED，且未领料）"""
        wo = await self.db.get(WorkOrder, wo_id)
        if not wo:
            raise ProductionError("工单不存在")
        if wo.status not in ("DRAFT", "RELEASED"):
            raise ProductionError(f"当前状态不可取消: {wo.status}")

        mats = (
            await self.db.execute(
                select(WorkOrderMaterial).where(
                    WorkOrderMaterial.work_order_id == wo_id
                )
            )
        ).scalars().all()
        if any(m.qty_issued > m.qty_returned for m in mats):
            raise ProductionError("已有净领料，请先退料后再取消")

        wo.status = "CANCELLED"
        return wo

    @staticmethod
    def progress_pct(plan_qty: Decimal, completed_qty: Decimal) -> float:
        if plan_qty <= 0:
            return 0.0
        return float(min(completed_qty / plan_qty * 100, 100))
