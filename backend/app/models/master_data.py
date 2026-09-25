"""基础数据模型：物料、供应商、仓库、单位等"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin, TimestampMixin


class Unit(Base, TimestampMixin):
    """计量单位"""
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Material(Base, AuditMixin):
    """物料主数据"""
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    spec: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    material_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="RAW"
    )  # RAW / SEMI / FG / CONSUMABLE
    base_unit: Mapped[str] = mapped_column(String(16), nullable=False, default="PCS")
    is_batch_managed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_roll_managed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Supplier(Base, AuditMixin):
    """供应商档案"""
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Customer(Base, AuditMixin):
    """客户档案"""
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    short_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    contact: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Warehouse(Base, TimestampMixin):
    """仓库"""
    __tablename__ = "warehouses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    warehouse_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="NORMAL"
    )  # NORMAL / WIP / QC / SCRAP
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Location(Base, TimestampMixin):
    """库位"""
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "code", name="uq_warehouse_location"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ReasonCode(Base, TimestampMixin):
    """原因码 / 状态字典"""
    __tablename__ = "reason_codes"
    __table_args__ = (
        UniqueConstraint("category", "code", name="uq_reason_category_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # ADJUST / SCRAP / FREEZE / QC_FAIL ...
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MaterialSupplier(Base, AuditMixin):
    """物料默认供应商（MRP 拆 PO 用）"""
    __tablename__ = "material_suppliers"
    __table_args__ = (
        UniqueConstraint("material_id", "supplier_id", name="uq_material_supplier"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    supplier_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    lead_time_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
