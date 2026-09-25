"""统计报表服务 —— 统一指标口径

所有周期报表调用同一套指标定义，避免日报与月报数字不一致。
"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from typing import Any, Optional

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockBalance, StockLedger
from app.models.production import OperationReport, WorkOrder
from app.models.purchase import ArrivalNote, IQCRecord, PurchaseOrder
from app.models.quality import InspectionRecord, QualityIssue


class ReportingService:
    """统一统计引擎"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _day_range(self, d: date) -> tuple[datetime, datetime]:
        start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        return start, end

    def _period_range(
        self, start: date, end: date
    ) -> tuple[datetime, datetime]:
        s = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
        e = datetime(end.year, end.month, end.day, tzinfo=timezone.utc) + timedelta(days=1)
        return s, e

    # ---------- 统一指标 ----------
    async def metric_purchase_receipt_qty(
        self, start: datetime, end: datetime
    ) -> Decimal:
        """采购入库数量（PURCHASE_IN 流水）"""
        result = await self.db.execute(
            select(func.coalesce(func.sum(StockLedger.qty), 0)).where(
                StockLedger.source_type == "PURCHASE_IN",
                StockLedger.created_at >= start,
                StockLedger.created_at < end,
            )
        )
        return Decimal(str(result.scalar_one()))

    async def metric_production_issue_qty(
        self, start: datetime, end: datetime
    ) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(func.abs(StockLedger.qty)), 0)).where(
                StockLedger.source_type == "PRODUCTION_ISSUE",
                StockLedger.created_at >= start,
                StockLedger.created_at < end,
            )
        )
        return Decimal(str(result.scalar_one()))

    async def metric_production_in_qty(
        self, start: datetime, end: datetime
    ) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(StockLedger.qty), 0)).where(
                StockLedger.source_type == "PRODUCTION_IN",
                StockLedger.created_at >= start,
                StockLedger.created_at < end,
            )
        )
        return Decimal(str(result.scalar_one()))

    async def metric_wo_completed_qty(
        self, start: datetime, end: datetime
    ) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(WorkOrder.completed_qty), 0)).where(
                WorkOrder.status.in_(["COMPLETED", "CLOSED", "IN_PROGRESS"]),
                WorkOrder.updated_at >= start,
                WorkOrder.updated_at < end,
            )
        )
        return Decimal(str(result.scalar_one()))

    async def metric_iqc_pass_rate(
        self, start: datetime, end: datetime
    ) -> Optional[Decimal]:
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(IQCRecord.qty_passed), 0),
                func.coalesce(func.sum(IQCRecord.qty_inspected), 0),
            ).where(
                IQCRecord.created_at >= start,
                IQCRecord.created_at < end,
            )
        )
        passed, inspected = result.one()
        inspected = Decimal(str(inspected))
        if inspected <= 0:
            return None
        return (Decimal(str(passed)) / inspected * 100).quantize(Decimal("0.01"))

    async def metric_open_quality_issues(self) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(QualityIssue).where(
                QualityIssue.status == "OPEN"
            )
        )
        return int(result.scalar_one())

    async def metric_stock_total_qty(self) -> Decimal:
        result = await self.db.execute(
            select(func.coalesce(func.sum(StockBalance.qty), 0))
        )
        return Decimal(str(result.scalar_one()))

    async def metric_po_count(self, start: datetime, end: datetime) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(PurchaseOrder).where(
                PurchaseOrder.created_at >= start,
                PurchaseOrder.created_at < end,
            )
        )
        return int(result.scalar_one())

    # ---------- 日报 ----------
    async def daily_report(self, report_date: date) -> dict[str, Any]:
        start, end = self._day_range(report_date)
        return {
            "report_date": report_date.isoformat(),
            "period_type": "daily",
            "metrics": {
                "purchase_receipt_qty": str(
                    await self.metric_purchase_receipt_qty(start, end)
                ),
                "production_issue_qty": str(
                    await self.metric_production_issue_qty(start, end)
                ),
                "production_in_qty": str(
                    await self.metric_production_in_qty(start, end)
                ),
                "wo_completed_qty": str(
                    await self.metric_wo_completed_qty(start, end)
                ),
                "iqc_pass_rate_pct": (
                    str(r)
                    if (r := await self.metric_iqc_pass_rate(start, end)) is not None
                    else None
                ),
                "open_quality_issues": await self.metric_open_quality_issues(),
                "stock_total_qty": str(await self.metric_stock_total_qty()),
                "po_created_count": await self.metric_po_count(start, end),
            },
        }

    async def period_report(self, start_date: date, end_date: date) -> dict[str, Any]:
        start, end = self._period_range(start_date, end_date)
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "period_type": "custom",
            "metrics": {
                "purchase_receipt_qty": str(
                    await self.metric_purchase_receipt_qty(start, end)
                ),
                "production_issue_qty": str(
                    await self.metric_production_issue_qty(start, end)
                ),
                "production_in_qty": str(
                    await self.metric_production_in_qty(start, end)
                ),
                "wo_completed_qty": str(
                    await self.metric_wo_completed_qty(start, end)
                ),
                "iqc_pass_rate_pct": (
                    str(r)
                    if (r := await self.metric_iqc_pass_rate(start, end)) is not None
                    else None
                ),
                "open_quality_issues": await self.metric_open_quality_issues(),
                "stock_total_qty": str(await self.metric_stock_total_qty()),
                "po_created_count": await self.metric_po_count(start, end),
            },
        }

    async def inventory_ledger_rows(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        source_type: Optional[str] = None,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        stmt = select(StockLedger).order_by(StockLedger.id.desc()).limit(limit)
        if start_date:
            s, _ = self._day_range(start_date)
            stmt = stmt.where(StockLedger.created_at >= s)
        if end_date:
            _, e = self._day_range(end_date)
            stmt = stmt.where(StockLedger.created_at < e)
        if source_type:
            stmt = stmt.where(StockLedger.source_type == source_type)
        rows = (await self.db.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "source_type": r.source_type,
                "source_id": r.source_id,
                "material_id": r.material_id,
                "warehouse_id": r.warehouse_id,
                "batch_no": r.batch_no,
                "qty": str(r.qty),
                "direction": r.direction,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    # ---------- Excel 导出 ----------
    def build_excel_bytes(
        self,
        sheets: dict[str, list[dict[str, Any]]],
    ) -> bytes:
        """
        sheets: { sheet_name: [ {col: val}, ... ] }
        需要 openpyxl；若不可用则抛错由调用方处理。
        """
        try:
            from openpyxl import Workbook
        except ImportError as e:
            raise RuntimeError("请安装 openpyxl: pip install openpyxl") from e

        wb = Workbook()
        # 删除默认 sheet
        default = wb.active
        first = True
        for name, rows in sheets.items():
            if first:
                ws = default
                ws.title = name[:31]
                first = False
            else:
                ws = wb.create_sheet(title=name[:31])
            if not rows:
                ws.append(["(无数据)"])
                continue
            headers = list(rows[0].keys())
            ws.append(headers)
            for row in rows:
                ws.append([row.get(h) for h in headers])
        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()

    async def export_daily_excel(self, report_date: date) -> bytes:
        report = await self.daily_report(report_date)
        metrics_rows = [
            {"metric": k, "value": v}
            for k, v in report["metrics"].items()
        ]
        ledgers = await self.inventory_ledger_rows(
            start_date=report_date, end_date=report_date, limit=1000
        )
        return self.build_excel_bytes(
            {
                "日报指标": metrics_rows,
                "当日流水": ledgers,
            }
        )

    async def export_ledger_excel(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        source_type: Optional[str] = None,
    ) -> bytes:
        rows = await self.inventory_ledger_rows(
            start_date=start_date,
            end_date=end_date,
            source_type=source_type,
            limit=5000,
        )
        return self.build_excel_bytes({"库存流水": rows})

    async def export_work_orders_excel(self) -> bytes:
        result = await self.db.execute(
            select(WorkOrder).order_by(WorkOrder.id.desc()).limit(500)
        )
        rows = []
        for wo in result.scalars().all():
            plan = wo.plan_qty or Decimal("0")
            done = wo.completed_qty or Decimal("0")
            pct = float(min(done / plan * 100, 100)) if plan else 0
            rows.append({
                "工单号": wo.doc_no,
                "状态": wo.status,
                "产品ID": wo.product_id,
                "版本ID": wo.product_version_id,
                "计划数量": float(plan),
                "完工数量": float(done),
                "报废数量": float(wo.scrap_qty or 0),
                "进度%": round(pct, 1),
                "领料仓": wo.warehouse_id,
                "成品仓": wo.fg_warehouse_id,
                "WIP仓": getattr(wo, "wip_warehouse_id", None),
            })
        return self.build_excel_bytes({"生产工单": rows})

    async def export_balances_excel(self) -> bytes:
        result = await self.db.execute(select(StockBalance).limit(2000))
        rows = []
        for b in result.scalars().all():
            avail = b.qty - b.qty_reserved - b.qty_frozen
            rows.append({
                "物料ID": b.material_id,
                "仓库ID": b.warehouse_id,
                "库位ID": b.location_id,
                "批次": b.batch_no,
                "卷号": b.roll_no,
                "数量": float(b.qty),
                "预留": float(b.qty_reserved),
                "冻结": float(b.qty_frozen),
                "可用": float(avail),
            })
        return self.build_excel_bytes({"库存余额": rows})
