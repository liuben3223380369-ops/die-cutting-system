"""期间结账 / 锁定

锁定后的会计期间禁止新增业务库存流水与关键单据变更。
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import AuditMixin


class AccountingPeriod(Base, AuditMixin):
    """会计期间"""
    __tablename__ = "accounting_periods"
    __table_args__ = (
        UniqueConstraint("year", "month", name="uq_period_year_month"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-12
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="OPEN"
    )  # OPEN / LOCKED
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    remark: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
