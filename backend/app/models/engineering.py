"""模切工程模型

核心原则：版本冻结 —— 历史生产引用的版本不能被后续修改影响。
正式发布的版本 status=RELEASED 后，内容只读；变更必须升版本。
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
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


class Product(Base, AuditMixin):
    """产品档案（逻辑产品，版本挂在下面）"""
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    customer_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    customer_part_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    material_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )  # 关联成品物料（可选）
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ProductVersion(Base, AuditMixin):
    """产品版本 —— 冻结单位

    status: DRAFT → RELEASED → OBSOLETE
    RELEASED 后禁止改 BOM/工艺/排版关联。
    """
    __tablename__ = "product_versions"
    __table_args__ = (
        UniqueConstraint("product_id", "version_code", name="uq_product_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    version_code: Mapped[str] = mapped_column(String(32), nullable=False)  # V1 / V1.1
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DRAFT"
    )  # DRAFT / RELEASED / OBSOLETE
    drawing_no: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    drawing_rev: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class BomHeader(Base, AuditMixin):
    """BOM 主表（绑定产品版本）"""
    __tablename__ = "bom_headers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_version_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class BomLine(Base, AuditMixin):
    """BOM 明细（含损耗与替代料）"""
    __tablename__ = "bom_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bom_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    qty_per: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False
    )  # 单位成品用量
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="PCS")
    scrap_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=0
    )  # 损耗率 0.05 = 5%
    is_alternative: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    alt_group: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)  # 替代组
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ProcessRoute(Base, AuditMixin):
    """工艺路线（绑定产品版本）"""
    __tablename__ = "process_routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_version_id: Mapped[int] = mapped_column(
        Integer, nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ProcessStep(Base, AuditMixin):
    """工序"""
    __tablename__ = "process_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    step_code: Mapped[str] = mapped_column(String(32), nullable=False)
    step_name: Mapped[str] = mapped_column(String(64), nullable=False)
    # 模切典型工序类型
    step_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="GENERAL"
    )  # SLITTING / LAMINATING / DIE_CUTTING / WASTE / SECONDARY / GENERAL
    work_center: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    std_time_sec: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    mold_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 关联模具
    param_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # 工序参数 JSON
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class Mold(Base, AuditMixin):
    """模具档案"""
    __tablename__ = "molds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    mold_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DIE"
    )  # DIE / KISS / STEEL_RULE
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="ACTIVE"
    )  # ACTIVE / MAINTENANCE / SCRAPPED
    life_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 寿命冲次
    life_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    product_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class NestingLayout(Base, AuditMixin):
    """排版版本（材料利用率计算基础）"""
    __tablename__ = "nesting_layouts"
    __table_args__ = (
        UniqueConstraint("product_version_id", "layout_code", name="uq_version_layout"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_version_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    layout_code: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    material_id: Mapped[int] = mapped_column(Integer, nullable=False)  # 主材料
    sheet_width: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    sheet_length: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    parts_per_sheet: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    utilization_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(8, 4), nullable=True
    )  # 材料利用率
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
