"""期间锁定服务"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.period import AccountingPeriod


class PeriodError(Exception):
    pass


class PeriodService:
    def __init__(self, db: AsyncSession, operator: str = "system"):
        self.db = db
        self.operator = operator

    async def ensure_period(self, year: int, month: int) -> AccountingPeriod:
        if month < 1 or month > 12:
            raise PeriodError("月份必须在 1-12")
        result = await self.db.execute(
            select(AccountingPeriod).where(
                AccountingPeriod.year == year,
                AccountingPeriod.month == month,
            )
        )
        p = result.scalar_one_or_none()
        if p:
            return p
        p = AccountingPeriod(
            year=year,
            month=month,
            status="OPEN",
            created_by=self.operator,
        )
        self.db.add(p)
        await self.db.flush()
        return p

    async def lock_period(self, year: int, month: int, remark: Optional[str] = None) -> AccountingPeriod:
        p = await self.ensure_period(year, month)
        if p.status == "LOCKED":
            raise PeriodError(f"{year}-{month:02d} 已锁定")
        p.status = "LOCKED"
        p.locked_at = datetime.now(timezone.utc)
        p.locked_by = self.operator
        if remark:
            p.remark = remark
        return p

    async def unlock_period(self, year: int, month: int) -> AccountingPeriod:
        p = await self.ensure_period(year, month)
        if p.status != "LOCKED":
            raise PeriodError(f"{year}-{month:02d} 未锁定")
        p.status = "OPEN"
        p.locked_at = None
        p.locked_by = None
        return p

    async def is_locked(self, d: date) -> bool:
        result = await self.db.execute(
            select(AccountingPeriod).where(
                AccountingPeriod.year == d.year,
                AccountingPeriod.month == d.month,
                AccountingPeriod.status == "LOCKED",
            )
        )
        return result.scalar_one_or_none() is not None

    async def assert_open(self, d: Optional[date] = None) -> None:
        """业务写入前调用：期间已锁定则拒绝"""
        d = d or date.today()
        if await self.is_locked(d):
            raise PeriodError(f"期间 {d.year}-{d.month:02d} 已锁定，禁止业务操作")

    async def list_periods(self, year: Optional[int] = None) -> list[AccountingPeriod]:
        stmt = select(AccountingPeriod).order_by(
            AccountingPeriod.year.desc(), AccountingPeriod.month.desc()
        )
        if year:
            stmt = stmt.where(AccountingPeriod.year == year)
        result = await self.db.execute(stmt.limit(36))
        return list(result.scalars().all())
