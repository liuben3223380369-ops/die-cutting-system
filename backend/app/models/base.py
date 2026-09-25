"""模型公共基类与混入"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TimestampMixin:
    """创建/更新时间混入"""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class AuditMixin(TimestampMixin):
    """审计字段混入（谁创建/修改）"""
    created_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
