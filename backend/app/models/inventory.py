"""库存核心模型：余额 + 流水（append-only）

核心原则：
1. 所有库存变化只能通过 stock_ledger 产生
2. 禁止直接修改 stock_balances.qty
3. 流水只增不改不删，错误用冲销（reversal）
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
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
from app.models.base import TimestampMixin


class StockBalance(Base, TimestampMixin):
    """库存余额（由流水汇总得出，禁止业务代码直接改 qty）"""
    __tablename__ = "stock_balances"
    __table_args__ = (
        UniqueConstraint(
            "material_id",
            "warehouse_id",
            "location_id",
            "batch_no",
            "roll_no",
            name="uq_stock_balance_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    roll_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    qty_reserved: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    qty_frozen: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    # 可用量 = qty - qty_reserved - qty_frozen（计算字段，不落库）


class StockLedger(Base):
    """库存流水（append-only，唯一事实源）

    每一笔库存变化必须产生一条流水。
    冲销时写入负数量流水，并关联 original_ledger_id。
    """
    __tablename__ = "stock_ledgers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 业务来源（可追溯）
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, index=True
    )  # PURCHASE_IN / PRODUCTION_OUT / TRANSFER / ADJUST / REVERSAL ...
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_line_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # 库存维度
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    warehouse_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    location_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    roll_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")

    # 数量：正数入库，负数出库
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="PCS")

    # 方向辅助（便于查询）
    direction: Mapped[str] = mapped_column(
        String(8), nullable=False
    )  # IN / OUT

    # 冲销关联
    original_ledger_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True
    )
    is_reversed: Mapped[bool] = mapped_column(default=False, nullable=False)

    # 备注与审计
    reason_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )


# 常用 source_type 常量
class StockSourceType:
    PURCHASE_IN = "PURCHASE_IN"          # 采购入库
    PURCHASE_RETURN = "PURCHASE_RETURN"  # 采购退货
    PRODUCTION_ISSUE = "PRODUCTION_ISSUE"  # 生产领料
    PRODUCTION_RETURN = "PRODUCTION_RETURN"  # 生产退料
    PRODUCTION_IN = "PRODUCTION_IN"      # 生产入库（半成品/成品）
    TRANSFER = "TRANSFER"                # 调拨（一出一入两条）
    ADJUST = "ADJUST"                    # 盘点调整
    FREEZE = "FREEZE"                    # 冻结（数量转移）
    UNFREEZE = "UNFREEZE"
    RESERVE = "RESERVE"
    UNRESERVE = "UNRESERVE"
    REVERSAL = "REVERSAL"                # 冲销
    QC_HOLD = "QC_HOLD"
    SCRAP = "SCRAP"
