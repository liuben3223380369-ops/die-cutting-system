"""质量与追溯服务"""
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockLedger
from app.models.production import OperationReport, WorkOrder
from app.models.purchase import ArrivalNote, ArrivalNoteLine, IQCRecord, PurchaseOrder
from app.models.quality import DefectCode, InspectionRecord, QualityIssue
from app.services.document_number import generate_document_number
from app.services.inventory import InventoryService
from app.models.inventory import StockSourceType


class QualityError(Exception):
    pass


class QualityService:
    def __init__(self, db: AsyncSession, operator: str = "system"):
        self.db = db
        self.operator = operator
        self.inv = InventoryService(db, operator)

    # ---------- 缺陷字典 ----------
    async def create_defect(self, code: str, name: str, category: str = "GENERAL") -> DefectCode:
        exists = await self.db.execute(select(DefectCode).where(DefectCode.code == code))
        if exists.scalar_one_or_none():
            raise QualityError(f"缺陷码已存在: {code}")
        obj = DefectCode(code=code, name=name, category=category, created_by=self.operator)
        self.db.add(obj)
        await self.db.flush()
        return obj

    # ---------- IPQC / FQC ----------
    async def create_inspection(
        self,
        inspect_type: str,
        result: str,
        qty_inspected: Decimal,
        qty_passed: Decimal,
        qty_failed: Decimal,
        inspect_date: date,
        material_id: Optional[int] = None,
        work_order_id: Optional[int] = None,
        operation_id: Optional[int] = None,
        batch_no: str = "",
        defect_codes: Optional[str] = None,
        inspector: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> InspectionRecord:
        if inspect_type not in ("IPQC", "FQC"):
            raise QualityError("inspect_type 必须是 IPQC 或 FQC")
        if qty_passed + qty_failed != qty_inspected:
            raise QualityError("合格+不合格必须等于检验数量")

        doc_no = await generate_document_number(self.db, "INS")
        rec = InspectionRecord(
            doc_no=doc_no,
            inspect_type=inspect_type,
            result=result,
            material_id=material_id,
            work_order_id=work_order_id,
            operation_id=operation_id,
            batch_no=batch_no or "",
            qty_inspected=qty_inspected,
            qty_passed=qty_passed,
            qty_failed=qty_failed,
            defect_codes=defect_codes,
            inspector=inspector or self.operator,
            inspect_date=inspect_date,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(rec)
        await self.db.flush()
        return rec

    # ---------- 质量异常 ----------
    async def create_issue(
        self,
        issue_type: str,
        qty: Decimal,
        material_id: Optional[int] = None,
        work_order_id: Optional[int] = None,
        batch_no: str = "",
        defect_codes: Optional[str] = None,
        description: Optional[str] = None,
        warehouse_id: Optional[int] = None,
        remark: Optional[str] = None,
    ) -> QualityIssue:
        doc_no = await generate_document_number(self.db, "QI")
        issue = QualityIssue(
            doc_no=doc_no,
            status="OPEN",
            issue_type=issue_type,
            material_id=material_id,
            work_order_id=work_order_id,
            batch_no=batch_no or "",
            qty=qty,
            defect_codes=defect_codes,
            description=description,
            warehouse_id=warehouse_id,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(issue)
        await self.db.flush()
        return issue

    async def dispose_issue(
        self,
        issue_id: int,
        disposition: str,
        hold_warehouse_id: Optional[int] = None,
    ) -> QualityIssue:
        """
        处置：REWORK / SCRAP / USE_AS_IS / RETURN
        SCRAP 时若指定仓库则出库记 SCRAP
        """
        issue = await self.db.get(QualityIssue, issue_id)
        if not issue:
            raise QualityError("异常单不存在")
        if issue.status == "CLOSED":
            raise QualityError("异常单已关闭")

        issue.disposition = disposition
        if disposition == "SCRAP" and issue.material_id and issue.qty > 0:
            wh = hold_warehouse_id or issue.warehouse_id
            if wh:
                try:
                    await self.inv.stock_out(
                        source_type=StockSourceType.SCRAP,
                        source_id=issue.doc_no,
                        material_id=issue.material_id,
                        warehouse_id=wh,
                        qty=issue.qty,
                        batch_no=issue.batch_no,
                        remark=f"质量报废 {issue.doc_no}",
                        allow_negative=False,
                    )
                except Exception as e:
                    raise QualityError(f"报废出库失败: {e}")

        issue.status = "CLOSED"
        return issue

    # ---------- 追溯 ----------
    async def forward_trace(self, material_id: int, batch_no: str = "") -> dict[str, Any]:
        """正向：某物料/批次 → 后续流向（出库、工单、成品）"""
        stmt = select(StockLedger).where(StockLedger.material_id == material_id)
        if batch_no:
            stmt = stmt.where(StockLedger.batch_no == batch_no)
        stmt = stmt.order_by(StockLedger.id)
        ledgers = (await self.db.execute(stmt)).scalars().all()

        flows = [
            {
                "ledger_id": l.id,
                "source_type": l.source_type,
                "source_id": l.source_id,
                "direction": l.direction,
                "qty": str(l.qty),
                "warehouse_id": l.warehouse_id,
                "batch_no": l.batch_no,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in ledgers
        ]

        # 关联工单
        wo_nos = {l.source_id for l in ledgers if l.source_type.startswith("PRODUCTION")}
        work_orders = []
        if wo_nos:
            result = await self.db.execute(
                select(WorkOrder).where(WorkOrder.doc_no.in_(wo_nos))
            )
            work_orders = [
                {"id": w.id, "doc_no": w.doc_no, "status": w.status, "product_id": w.product_id}
                for w in result.scalars().all()
            ]

        return {
            "material_id": material_id,
            "batch_no": batch_no,
            "ledgers": flows,
            "work_orders": work_orders,
        }

    async def reverse_trace(self, source_type: str, source_id: str) -> dict[str, Any]:
        """反向：从成品入库单/工单号反查原料与检验"""
        stmt = (
            select(StockLedger)
            .where(
                StockLedger.source_type == source_type,
                StockLedger.source_id == source_id,
            )
            .order_by(StockLedger.id)
        )
        ledgers = (await self.db.execute(stmt)).scalars().all()

        # 若是工单，找领料流水
        related = []
        if source_type in ("PRODUCTION_IN", "WO") or source_id.startswith("WO"):
            wo_no = source_id
            if source_type == "PRODUCTION_IN":
                wo_no = source_id
            issue_ledgers = (
                await self.db.execute(
                    select(StockLedger).where(
                        StockLedger.source_type == StockSourceType.PRODUCTION_ISSUE,
                        StockLedger.source_id == wo_no,
                    )
                )
            ).scalars().all()
            related = [
                {
                    "ledger_id": l.id,
                    "source_type": l.source_type,
                    "material_id": l.material_id,
                    "qty": str(l.qty),
                    "batch_no": l.batch_no,
                }
                for l in issue_ledgers
            ]

            # IQC 关联：按批次反查
            batches = {l.batch_no for l in issue_ledgers if l.batch_no}
            iqc_list = []
            if batches:
                for b in batches:
                    iqcs = (
                        await self.db.execute(
                            select(IQCRecord)
                            .join(ArrivalNoteLine, ArrivalNoteLine.id == IQCRecord.arrival_line_id)
                            .where(ArrivalNoteLine.batch_no == b)
                        )
                    ).scalars().all()
                    for q in iqcs:
                        iqc_list.append({
                            "doc_no": q.doc_no,
                            "result": q.result,
                            "qty_passed": str(q.qty_passed),
                            "qty_failed": str(q.qty_failed),
                        })
            else:
                iqc_list = []

            return {
                "source_type": source_type,
                "source_id": source_id,
                "ledgers": [
                    {
                        "ledger_id": l.id,
                        "source_type": l.source_type,
                        "material_id": l.material_id,
                        "qty": str(l.qty),
                        "direction": l.direction,
                    }
                    for l in ledgers
                ],
                "material_issues": related,
                "iqc_records": iqc_list,
            }

        return {
            "source_type": source_type,
            "source_id": source_id,
            "ledgers": [
                {
                    "ledger_id": l.id,
                    "source_type": l.source_type,
                    "material_id": l.material_id,
                    "qty": str(l.qty),
                    "direction": l.direction,
                    "batch_no": l.batch_no,
                }
                for l in ledgers
            ],
        }
