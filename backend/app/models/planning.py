"""计划 / MRP 模型

销售订单 → 需求展开 → 净需求 → 采购建议 / 生产建议
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class SalesOrder(Base, AuditMixin):
    """销售订单头"""
    __tablename__ = "sales_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DRAFT"
    )  # DRAFT / CONFIRMED / PARTIAL / CLOSED / CANCELLED
    customer_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    order_date: Mapped[date] = mapped_column(Date, nullable=False)
    required_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SalesOrderLine(Base, AuditMixin):
    """销售订单明细"""
    __tablename__ = "sales_order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    product_version_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 锁定版本，空则取最新 RELEASED
    material_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 成品物料
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    qty_shipped: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="PCS")
    required_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class MrpRun(Base, AuditMixin):
    """一次 MRP 运算记录（可追溯）"""
    __tablename__ = "mrp_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DONE"
    )  # RUNNING / DONE / FAILED
    sales_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class MrpRequirement(Base, AuditMixin):
    """MRP 需求明细（毛需求 / 净需求 / 建议）"""
    __tablename__ = "mrp_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # BOM 层级
    gross_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    on_hand_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    reserved_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    on_order_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)  # 在途采购
    net_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    suggestion_type: Mapped[str] = mapped_column(
        String(16), nullable=False, default="NONE"
    )  # PURCHASE / PRODUCE / NONE
    suggestion_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    source_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    parent_material_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
