"""采购模块模型

流程：采购申请(PR) → 采购订单(PO) → 到货登记 → IQC → 合格入库 / 不合格隔离
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class PurchaseRequest(Base, AuditMixin):
    """采购申请单头"""
    __tablename__ = "purchase_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DRAFT"
    )  # DRAFT / SUBMITTED / APPROVED / CLOSED / CANCELLED
    request_date: Mapped[date] = mapped_column(Date, nullable=False)
    requester: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PurchaseRequestLine(Base, AuditMixin):
    """采购申请明细"""
    __tablename__ = "purchase_request_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="PCS")
    required_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PurchaseOrder(Base, AuditMixin):
    """采购订单头"""
    __tablename__ = "purchase_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DRAFT"
    )  # DRAFT / CONFIRMED / PARTIAL / COMPLETED / CLOSED / CANCELLED
    supplier_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    expected_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # 来源申请（可选）
    request_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class PurchaseOrderLine(Base, AuditMixin):
    """采购订单明细"""
    __tablename__ = "purchase_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    qty_received: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="PCS")
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)
    expected_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ArrivalNote(Base, AuditMixin):
    """到货登记单"""
    __tablename__ = "arrival_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DRAFT"
    )  # DRAFT / RECEIVED / QC_DONE / CLOSED
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(Integer, nullable=False)
    arrival_date: Mapped[date] = mapped_column(Date, nullable=False)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 暂收仓
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ArrivalNoteLine(Base, AuditMixin):
    """到货明细"""
    __tablename__ = "arrival_note_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arrival_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    order_line_id: Mapped[int] = mapped_column(Integer, nullable=False)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="PCS")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    roll_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # IQC 结果
    qc_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING"
    )  # PENDING / PASSED / FAILED / PARTIAL
    qty_passed: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    qty_failed: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class IQCRecord(Base, AuditMixin):
    """IQC 检验记录"""
    __tablename__ = "iqc_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    arrival_line_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # PASSED / FAILED / PARTIAL
    qty_inspected: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    qty_passed: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    qty_failed: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    inspector: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    inspect_date: Mapped[date] = mapped_column(Date, nullable=False)
    defect_codes: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PurchaseReturn(Base, AuditMixin):
    """采购退货单头"""
    __tablename__ = "purchase_returns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DRAFT"
    )  # DRAFT / CONFIRMED / CANCELLED
    supplier_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    return_date: Mapped[date] = mapped_column(Date, nullable=False)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PurchaseReturnLine(Base, AuditMixin):
    """采购退货明细"""
    __tablename__ = "purchase_return_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    return_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="PCS")
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    roll_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    order_line_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PurchasePriceHistory(Base, AuditMixin):
    """采购价格历史（下单/到货时记录）"""
    __tablename__ = "purchase_price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    supplier_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, default="PO")
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
