"""生产模块模型

核心原则：
- 工单创建时锁定 product_version / BOM / 工艺 / 排版版本
- 工序数量、WIP、良品、不良、报废守恒可追溯
- 领料/退料/入库全部走 InventoryService
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class WorkOrder(Base, AuditMixin):
    """生产工单"""
    __tablename__ = "work_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DRAFT"
    )  # DRAFT / RELEASED / IN_PROGRESS / COMPLETED / CLOSED / CANCELLED

    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # 锁定版本（创建后不可改）
    product_version_id: Mapped[int] = mapped_column(Integer, nullable=False)
    bom_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    route_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nesting_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    plan_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    completed_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    scrap_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="PCS")

    warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 领料仓
    fg_warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 成品仓
    wip_warehouse_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 在制品仓
    plan_start: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    plan_end: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sales_order_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class WorkOrderMaterial(Base, AuditMixin):
    """工单物料需求（由 BOM 展开锁定）"""
    __tablename__ = "work_order_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qty_required: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    qty_issued: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    qty_returned: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="PCS")


class WorkOrderOperation(Base, AuditMixin):
    """工单工序（由工艺路线复制锁定）"""
    __tablename__ = "work_order_operations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    step_code: Mapped[str] = mapped_column(String(32), nullable=False)
    step_name: Mapped[str] = mapped_column(String(64), nullable=False)
    step_type: Mapped[str] = mapped_column(String(32), nullable=False, default="GENERAL")
    mold_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="PENDING"
    )  # PENDING / RUNNING / DONE
    qty_good: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    qty_reject: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    qty_scrap: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)


class OperationReport(Base, AuditMixin):
    """工序报工记录"""
    __tablename__ = "operation_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    work_order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    operation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qty_good: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    qty_reject: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    qty_scrap: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    operator_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    downtime_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
