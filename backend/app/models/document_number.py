"""业务单据编号序列"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DocumentSequence(Base):
    """单据编号序列表（按类型+日期维护当前序号）"""
    __tablename__ = "document_sequences"
    __table_args__ = (
        UniqueConstraint("doc_type", "date_key", name="uq_doc_type_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    date_key: Mapped[str] = mapped_column(String(8), nullable=False)  # YYYYMMDD
    current_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prefix: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
