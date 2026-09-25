"""工程服务 —— 版本冻结是核心

RELEASED 的产品版本，其 BOM / 工艺 / 排版不可再改。
变更必须新建版本。
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engineering import (
    BomHeader,
    BomLine,
    Mold,
    NestingLayout,
    ProcessRoute,
    ProcessStep,
    Product,
    ProductVersion,
)


class EngineeringError(Exception):
    pass


class VersionFrozenError(EngineeringError):
    """版本已发布，禁止修改"""
    pass


class EngineeringService:
    def __init__(self, db: AsyncSession, operator: str = "system"):
        self.db = db
        self.operator = operator

    async def _get_version(self, version_id: int) -> ProductVersion:
        v = await self.db.get(ProductVersion, version_id)
        if not v:
            raise EngineeringError("产品版本不存在")
        return v

    def _ensure_draft(self, version: ProductVersion) -> None:
        if version.status == "RELEASED":
            raise VersionFrozenError(
                f"版本 {version.version_code} 已发布，禁止修改；请新建版本"
            )
        if version.status == "OBSOLETE":
            raise VersionFrozenError(f"版本 {version.version_code} 已作废")

    # ---------- Product ----------
    async def create_product(self, **kwargs) -> Product:
        exists = await self.db.execute(
            select(Product).where(Product.code == kwargs["code"])
        )
        if exists.scalar_one_or_none():
            raise EngineeringError(f"产品编码已存在: {kwargs['code']}")
        obj = Product(**kwargs, created_by=self.operator)
        self.db.add(obj)
        await self.db.flush()
        return obj

    # ---------- Version ----------
    async def create_version(
        self,
        product_id: int,
        version_code: str,
        drawing_no: Optional[str] = None,
        drawing_rev: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> ProductVersion:
        product = await self.db.get(Product, product_id)
        if not product:
            raise EngineeringError("产品不存在")
        exists = await self.db.execute(
            select(ProductVersion).where(
                ProductVersion.product_id == product_id,
                ProductVersion.version_code == version_code,
            )
        )
        if exists.scalar_one_or_none():
            raise EngineeringError(f"版本号已存在: {version_code}")

        v = ProductVersion(
            product_id=product_id,
            version_code=version_code,
            status="DRAFT",
            drawing_no=drawing_no,
            drawing_rev=drawing_rev,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(v)
        await self.db.flush()
        return v

    async def release_version(self, version_id: int) -> ProductVersion:
        """发布版本：要求已有 BOM 和工艺路线"""
        v = await self._get_version(version_id)
        if v.status != "DRAFT":
            raise EngineeringError(f"仅草稿可发布，当前: {v.status}")

        bom = (
            await self.db.execute(
                select(BomHeader).where(BomHeader.product_version_id == version_id)
            )
        ).scalar_one_or_none()
        route = (
            await self.db.execute(
                select(ProcessRoute).where(
                    ProcessRoute.product_version_id == version_id
                )
            )
        ).scalar_one_or_none()
        if not bom:
            raise EngineeringError("发布前必须维护 BOM")
        if not route:
            raise EngineeringError("发布前必须维护工艺路线")

        # 检查 BOM/路线有明细
        bom_lines = (
            await self.db.execute(select(BomLine).where(BomLine.bom_id == bom.id))
        ).scalars().all()
        steps = (
            await self.db.execute(
                select(ProcessStep).where(ProcessStep.route_id == route.id)
            )
        ).scalars().all()
        if not bom_lines:
            raise EngineeringError("BOM 无明细，无法发布")
        if not steps:
            raise EngineeringError("工艺路线无工序，无法发布")

        v.status = "RELEASED"
        v.released_at = datetime.now(timezone.utc)
        bom.status = "RELEASED"
        route.status = "RELEASED"
        return v

    # ---------- BOM ----------
    async def save_bom(
        self,
        product_version_id: int,
        lines: list[dict],
        remark: Optional[str] = None,
    ) -> BomHeader:
        v = await self._get_version(product_version_id)
        self._ensure_draft(v)

        bom = (
            await self.db.execute(
                select(BomHeader).where(
                    BomHeader.product_version_id == product_version_id
                )
            )
        ).scalar_one_or_none()

        if bom is None:
            bom = BomHeader(
                product_version_id=product_version_id,
                status="DRAFT",
                remark=remark,
                created_by=self.operator,
            )
            self.db.add(bom)
            await self.db.flush()
        else:
            bom.remark = remark
            # 删除旧明细
            old = (
                await self.db.execute(
                    select(BomLine).where(BomLine.bom_id == bom.id)
                )
            ).scalars().all()
            for o in old:
                await self.db.delete(o)
            await self.db.flush()

        for i, line in enumerate(lines, start=1):
            bl = BomLine(
                bom_id=bom.id,
                line_no=i,
                material_id=line["material_id"],
                qty_per=line["qty_per"],
                unit=line.get("unit", "PCS"),
                scrap_rate=line.get("scrap_rate", Decimal("0")),
                is_alternative=line.get("is_alternative", False),
                alt_group=line.get("alt_group"),
                priority=line.get("priority", 1),
                remark=line.get("remark"),
                created_by=self.operator,
            )
            self.db.add(bl)
        await self.db.flush()
        return bom

    async def get_bom(self, product_version_id: int) -> Optional[BomHeader]:
        return (
            await self.db.execute(
                select(BomHeader).where(
                    BomHeader.product_version_id == product_version_id
                )
            )
        ).scalar_one_or_none()

    def calc_gross_qty(self, qty_per: Decimal, scrap_rate: Decimal, order_qty: Decimal) -> Decimal:
        """含损耗毛需求 = 订单数量 × 单位用量 × (1 + 损耗率)"""
        return order_qty * qty_per * (Decimal("1") + scrap_rate)

    # ---------- Process Route ----------
    async def save_route(
        self,
        product_version_id: int,
        steps: list[dict],
        remark: Optional[str] = None,
    ) -> ProcessRoute:
        v = await self._get_version(product_version_id)
        self._ensure_draft(v)

        route = (
            await self.db.execute(
                select(ProcessRoute).where(
                    ProcessRoute.product_version_id == product_version_id
                )
            )
        ).scalar_one_or_none()

        if route is None:
            route = ProcessRoute(
                product_version_id=product_version_id,
                status="DRAFT",
                remark=remark,
                created_by=self.operator,
            )
            self.db.add(route)
            await self.db.flush()
        else:
            route.remark = remark
            old = (
                await self.db.execute(
                    select(ProcessStep).where(ProcessStep.route_id == route.id)
                )
            ).scalars().all()
            for o in old:
                await self.db.delete(o)
            await self.db.flush()

        for step in steps:
            ps = ProcessStep(
                route_id=route.id,
                seq=step.get("seq", 10),
                step_code=step["step_code"],
                step_name=step["step_name"],
                step_type=step.get("step_type", "GENERAL"),
                work_center=step.get("work_center"),
                std_time_sec=step.get("std_time_sec"),
                mold_id=step.get("mold_id"),
                param_json=step.get("param_json"),
                remark=step.get("remark"),
                created_by=self.operator,
            )
            self.db.add(ps)
        await self.db.flush()
        return route

    # ---------- Mold ----------
    async def create_mold(self, **kwargs) -> Mold:
        exists = await self.db.execute(
            select(Mold).where(Mold.code == kwargs["code"])
        )
        if exists.scalar_one_or_none():
            raise EngineeringError(f"模具编码已存在: {kwargs['code']}")
        obj = Mold(**kwargs, created_by=self.operator)
        self.db.add(obj)
        await self.db.flush()
        return obj

    async def add_mold_usage(self, mold_id: int, hits: int) -> Mold:
        """累计模具使用冲次，达到寿命自动标记维护"""
        mold = await self.db.get(Mold, mold_id)
        if not mold:
            raise EngineeringError("模具不存在")
        mold.life_used += hits
        if mold.life_limit and mold.life_used >= mold.life_limit:
            mold.status = "MAINTENANCE"
        return mold

    # ---------- Nesting ----------
    async def create_nesting(self, **kwargs) -> NestingLayout:
        v = await self._get_version(kwargs["product_version_id"])
        self._ensure_draft(v)
        obj = NestingLayout(**kwargs, status="DRAFT", created_by=self.operator)
        self.db.add(obj)
        await self.db.flush()
        return obj

    def calc_utilization(
        self,
        part_area: Decimal,
        parts_per_sheet: int,
        sheet_width: Decimal,
        sheet_length: Decimal,
    ) -> Decimal:
        """材料利用率 = (零件面积 × 排数) / 板材面积"""
        sheet_area = sheet_width * sheet_length
        if sheet_area <= 0:
            return Decimal("0")
        return (part_area * parts_per_sheet) / sheet_area
