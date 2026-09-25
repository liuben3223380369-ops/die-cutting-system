"""成本模块 —— 实际消耗归集

理论（BOM）与实际（领料/报工）分离，按工单归集。
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class MaterialStandardCost(Base, AuditMixin):
    """物料标准成本"""
    __tablename__ = "material_standard_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class WorkOrderCost(Base, AuditMixin):
    """工单成本汇总"""
    __tablename__ = "work_order_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_order_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    material_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    scrap_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    mold_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    process_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=0)
    completed_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="CNY")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
