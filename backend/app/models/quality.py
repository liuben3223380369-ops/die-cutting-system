"""质量模块

IQC 已在采购模块；此处覆盖 IPQC / FQC、缺陷、质量异常、隔离处置。
追溯依赖 stock_ledger + 业务单据 source_type/source_id。
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class DefectCode(Base, AuditMixin):
    """缺陷字典"""
    __tablename__ = "defect_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str] = mapped_column(
        String(32), nullable=False, default="GENERAL"
    )  # APPEARANCE / DIMENSION / FUNCTION / GENERAL
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)


class InspectionRecord(Base, AuditMixin):
    """通用检验记录（IPQC / FQC，IQC 仍用 iqc_records）"""
    __tablename__ = "inspection_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    inspect_type: Mapped[str] = mapped_column(
        String(16), nullable=False, index=True
    )  # IPQC / FQC
    result: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # PASSED / FAILED / PARTIAL
    material_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    work_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    operation_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    qty_inspected: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    qty_passed: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    qty_failed: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    defect_codes: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    inspector: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    inspect_date: Mapped[date] = mapped_column(Date, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class QualityIssue(Base, AuditMixin):
    """质量异常单"""
    __tablename__ = "quality_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="OPEN"
    )  # OPEN / IN_PROCESS / CLOSED
    issue_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DEFECT"
    )  # DEFECT / CUSTOMER_COMPLAINT / PROCESS
    material_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    work_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    defect_codes: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    disposition: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True
    )  # REWORK / SCRAP / USE_AS_IS / RETURN
    warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
