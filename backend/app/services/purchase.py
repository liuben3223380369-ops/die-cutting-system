"""采购服务

关键闭环：
  到货登记 → IQC → 合格部分 stock_in(PURCHASE_IN)
                 → 不合格部分 可选转入隔离仓
"""
from datetime import date
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
from app.models.inventory import StockSourceType
from app.services.document_number import generate_document_number
from app.services.inventory import InventoryService, InventoryError


class PurchaseError(Exception):
    pass


class PurchaseService:
    def __init__(self, db: AsyncSession, operator: str = "system"):
        self.db = db
        self.operator = operator
        self.inv = InventoryService(db, operator)

    # ---------- 采购申请 ----------
    async def create_request(
        self,
        request_date: date,
        lines: list[dict],
        requester: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> PurchaseRequest:
        doc_no = await generate_document_number(self.db, "PR")
        pr = PurchaseRequest(
            doc_no=doc_no,
            status="DRAFT",
            request_date=request_date,
            requester=requester,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(pr)
        await self.db.flush()

        for i, line in enumerate(lines, start=1):
            pl = PurchaseRequestLine(
                request_id=pr.id,
                line_no=i,
                material_id=line["material_id"],
                qty=line["qty"],
                unit=line.get("unit", "PCS"),
                required_date=line.get("required_date"),
                remark=line.get("remark"),
                created_by=self.operator,
            )
            self.db.add(pl)
        await self.db.flush()
        return pr

    async def submit_request(self, request_id: int) -> PurchaseRequest:
        pr = await self.db.get(PurchaseRequest, request_id)
        if not pr:
            raise PurchaseError("采购申请不存在")
        if pr.status != "DRAFT":
            raise PurchaseError(f"当前状态不可提交: {pr.status}")
        pr.status = "SUBMITTED"
        return pr

    # ---------- 采购订单 ----------
    async def create_order(
        self,
        supplier_id: int,
        order_date: date,
        lines: list[dict],
        expected_date: Optional[date] = None,
        currency: str = "CNY",
        remark: Optional[str] = None,
        request_id: Optional[int] = None,
    ) -> PurchaseOrder:
        doc_no = await generate_document_number(self.db, "PO")
        po = PurchaseOrder(
            doc_no=doc_no,
            status="DRAFT",
            supplier_id=supplier_id,
            order_date=order_date,
            expected_date=expected_date,
            currency=currency,
            remark=remark,
            request_id=request_id,
            created_by=self.operator,
        )
        self.db.add(po)
        await self.db.flush()

        for i, line in enumerate(lines, start=1):
            pl = PurchaseOrderLine(
                order_id=po.id,
                line_no=i,
                material_id=line["material_id"],
                qty=line["qty"],
                qty_received=Decimal("0"),
                unit=line.get("unit", "PCS"),
                unit_price=line.get("unit_price"),
                expected_date=line.get("expected_date"),
                remark=line.get("remark"),
                created_by=self.operator,
            )
            self.db.add(pl)
        await self.db.flush()
        return po

    async def confirm_order(self, order_id: int) -> PurchaseOrder:
        po = await self.db.get(PurchaseOrder, order_id)
        if not po:
            raise PurchaseError("采购订单不存在")
        if po.status != "DRAFT":
            raise PurchaseError(f"当前状态不可确认: {po.status}")
        po.status = "CONFIRMED"
        # 记录价格历史
        result = await self.db.execute(
            select(PurchaseOrderLine).where(PurchaseOrderLine.order_id == po.id)
        )
        for line in result.scalars().all():
            if line.unit_price is not None:
                await self.record_price_history(
                    supplier_id=po.supplier_id,
                    material_id=line.material_id,
                    unit_price=line.unit_price,
                    effective_date=po.order_date,
                    source_type="PO",
                    source_id=po.doc_no,
                    currency=po.currency,
                )
        return po

    # ---------- 到货登记 ----------
    async def create_arrival(
        self,
        order_id: int,
        arrival_date: date,
        warehouse_id: int,
        lines: list[dict],
        remark: Optional[str] = None,
    ) -> ArrivalNote:
        po = await self.db.get(PurchaseOrder, order_id)
        if not po:
            raise PurchaseError("采购订单不存在")
        if po.status not in ("CONFIRMED", "PARTIAL"):
            raise PurchaseError(f"订单状态不可到货: {po.status}")

        doc_no = await generate_document_number(self.db, "AR")
        note = ArrivalNote(
            doc_no=doc_no,
            status="RECEIVED",
            order_id=order_id,
            supplier_id=po.supplier_id,
            arrival_date=arrival_date,
            warehouse_id=warehouse_id,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(note)
        await self.db.flush()

        for i, line in enumerate(lines, start=1):
            # 校验订单行
            ol = await self.db.get(PurchaseOrderLine, line["order_line_id"])
            if not ol or ol.order_id != order_id:
                raise PurchaseError(f"订单行无效: {line['order_line_id']}")
            remaining = ol.qty - ol.qty_received
            if line["qty"] > remaining:
                raise PurchaseError(
                    f"到货数量超过订单剩余: 行{ol.line_no} 剩余{remaining}"
                )

            al = ArrivalNoteLine(
                arrival_id=note.id,
                line_no=i,
                order_line_id=line["order_line_id"],
                material_id=line["material_id"],
                qty=line["qty"],
                unit=line.get("unit", "PCS"),
                batch_no=line.get("batch_no", ""),
                roll_no=line.get("roll_no", ""),
                qc_status="PENDING",
                qty_passed=Decimal("0"),
                qty_failed=Decimal("0"),
                remark=line.get("remark"),
                created_by=self.operator,
            )
            self.db.add(al)
            # 更新订单已收数量
            ol.qty_received += line["qty"]

        # 更新订单状态
        await self.db.flush()
        result = await self.db.execute(
            select(PurchaseOrderLine).where(PurchaseOrderLine.order_id == order_id)
        )
        all_lines = result.scalars().all()
        if all(l.qty_received >= l.qty for l in all_lines):
            po.status = "COMPLETED"
        else:
            po.status = "PARTIAL"

        return note

    # ---------- IQC + 合格入库 ----------
    async def do_iqc(
        self,
        arrival_line_id: int,
        result: str,
        qty_inspected: Decimal,
        qty_passed: Decimal,
        qty_failed: Decimal,
        inspect_date: date,
        inspector: Optional[str] = None,
        defect_codes: Optional[str] = None,
        remark: Optional[str] = None,
        target_warehouse_id: Optional[int] = None,
        hold_warehouse_id: Optional[int] = None,
    ) -> IQCRecord:
        """
        IQC 检验并驱动库存：
        - 合格数量 → 目标仓 stock_in(PURCHASE_IN)
        - 不合格数量 → 隔离仓（若指定）或仅记录
        """
        al = await self.db.get(ArrivalNoteLine, arrival_line_id)
        if not al:
            raise PurchaseError("到货明细不存在")
        if al.qc_status != "PENDING":
            raise PurchaseError(f"该行已检验: {al.qc_status}")

        if qty_passed + qty_failed != qty_inspected:
            raise PurchaseError("合格+不合格数量必须等于检验数量")
        if qty_inspected > al.qty:
            raise PurchaseError("检验数量不能超过到货数量")

        note = await self.db.get(ArrivalNote, al.arrival_id)
        if not note:
            raise PurchaseError("到货单不存在")

        doc_no = await generate_document_number(self.db, "QC")
        iqc = IQCRecord(
            doc_no=doc_no,
            arrival_line_id=arrival_line_id,
            material_id=al.material_id,
            result=result,
            qty_inspected=qty_inspected,
            qty_passed=qty_passed,
            qty_failed=qty_failed,
            inspector=inspector,
            inspect_date=inspect_date,
            defect_codes=defect_codes,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(iqc)
        await self.db.flush()

        # 更新到货行 QC 状态
        al.qty_passed = qty_passed
        al.qty_failed = qty_failed
        al.qc_status = result

        # ---- 库存动作 ----
        # 合格入库
        if qty_passed > 0:
            wh_id = target_warehouse_id or note.warehouse_id
            await self.inv.stock_in(
                source_type=StockSourceType.PURCHASE_IN,
                source_id=note.doc_no,
                source_line_id=str(al.id),
                material_id=al.material_id,
                warehouse_id=wh_id,
                qty=qty_passed,
                batch_no=al.batch_no,
                roll_no=al.roll_no,
                unit=al.unit,
                remark=f"IQC合格入库 {iqc.doc_no}",
            )

        # 不合格隔离（可选：转入隔离仓）
        if qty_failed > 0 and hold_warehouse_id:
            await self.inv.stock_in(
                source_type=StockSourceType.QC_HOLD,
                source_id=note.doc_no,
                source_line_id=str(al.id),
                material_id=al.material_id,
                warehouse_id=hold_warehouse_id,
                qty=qty_failed,
                batch_no=al.batch_no,
                roll_no=al.roll_no,
                unit=al.unit,
                remark=f"IQC不合格隔离 {iqc.doc_no}",
            )

        # 更新到货单状态
        result_lines = await self.db.execute(
            select(ArrivalNoteLine).where(ArrivalNoteLine.arrival_id == note.id)
        )
        lines = result_lines.scalars().all()
        if all(l.qc_status != "PENDING" for l in lines):
            note.status = "QC_DONE"

        return iqc


    # ---------- 采购退货 ----------
    async def create_return(
        self,
        supplier_id: int,
        return_date: date,
        warehouse_id: int,
        lines: list[dict],
        order_id: Optional[int] = None,
        reason_code: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> PurchaseReturn:
        """创建退货单（草稿）"""
        doc_no = await generate_document_number(self.db, "RT")
        ret = PurchaseReturn(
            doc_no=doc_no,
            status="DRAFT",
            supplier_id=supplier_id,
            order_id=order_id,
            return_date=return_date,
            warehouse_id=warehouse_id,
            reason_code=reason_code,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(ret)
        await self.db.flush()

        for i, line in enumerate(lines, start=1):
            rl = PurchaseReturnLine(
                return_id=ret.id,
                line_no=i,
                material_id=line["material_id"],
                qty=line["qty"],
                unit=line.get("unit", "PCS"),
                batch_no=line.get("batch_no", ""),
                roll_no=line.get("roll_no", ""),
                order_line_id=line.get("order_line_id"),
                remark=line.get("remark"),
                created_by=self.operator,
            )
            self.db.add(rl)
        await self.db.flush()
        return ret

    async def confirm_return(self, return_id: int) -> PurchaseReturn:
        """确认退货：从仓库出库（PURCHASE_RETURN）"""
        ret = await self.db.get(PurchaseReturn, return_id)
        if not ret:
            raise PurchaseError("退货单不存在")
        if ret.status != "DRAFT":
            raise PurchaseError(f"当前状态不可确认: {ret.status}")

        result = await self.db.execute(
            select(PurchaseReturnLine).where(PurchaseReturnLine.return_id == ret.id)
        )
        lines = result.scalars().all()
        if not lines:
            raise PurchaseError("退货单无明细")

        for line in lines:
            await self.inv.stock_out(
                source_type=StockSourceType.PURCHASE_RETURN,
                source_id=ret.doc_no,
                source_line_id=str(line.id),
                material_id=line.material_id,
                warehouse_id=ret.warehouse_id,
                qty=line.qty,
                batch_no=line.batch_no,
                roll_no=line.roll_no,
                unit=line.unit,
                remark=f"采购退货 {ret.doc_no}",
            )

        ret.status = "CONFIRMED"
        return ret

    async def record_price_history(
        self,
        supplier_id: int,
        material_id: int,
        unit_price: Decimal,
        effective_date: date,
        source_type: str,
        source_id: str,
        currency: str = "CNY",
        remark: Optional[str] = None,
    ) -> PurchasePriceHistory:
        """记录采购价格历史"""
        rec = PurchasePriceHistory(
            supplier_id=supplier_id,
            material_id=material_id,
            unit_price=unit_price,
            currency=currency,
            effective_date=effective_date,
            source_type=source_type,
            source_id=source_id,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(rec)
        await self.db.flush()
        return rec

    # ---------- 查询辅助 ----------
    async def get_order_with_lines(self, order_id: int) -> Optional[PurchaseOrder]:
        stmt = (
            select(PurchaseOrder)
            .where(PurchaseOrder.id == order_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
