"""MRP / 计划服务

算法概要：
1. 取销售订单行 → 锁定产品版本（或最新 RELEASED）
2. 多级 BOM 展开（含损耗）得到毛需求
3. 扣减：可用库存 + 在途采购（CONFIRMED/PARTIAL PO 未收完）
4. 净需求 > 0 → 原料建议采购，半成品/成品建议生产
"""
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engineering import (
    BomHeader,
    BomLine,
    Product,
    ProductVersion,
)
from app.models.inventory import StockBalance
from app.models.master_data import Material
from app.models.planning import (
    MrpRequirement,
    MrpRun,
    SalesOrder,
    SalesOrderLine,
)
from app.models.purchase import PurchaseOrder, PurchaseOrderLine
from app.services.document_number import generate_document_number


class PlanningError(Exception):
    pass


class PlanningService:
    def __init__(self, db: AsyncSession, operator: str = "system"):
        self.db = db
        self.operator = operator

    # ---------- 销售订单 ----------
    async def create_sales_order(
        self,
        customer_id: int,
        order_date: date,
        lines: list[dict],
        required_date: Optional[date] = None,
        remark: Optional[str] = None,
    ) -> SalesOrder:
        doc_no = await generate_document_number(self.db, "SO")
        so = SalesOrder(
            doc_no=doc_no,
            status="DRAFT",
            customer_id=customer_id,
            order_date=order_date,
            required_date=required_date,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(so)
        await self.db.flush()

        for i, line in enumerate(lines, start=1):
            # 若未指定版本，取该产品最新 RELEASED
            version_id = line.get("product_version_id")
            if not version_id:
                version_id = await self._latest_released_version(line["product_id"])

            sl = SalesOrderLine(
                order_id=so.id,
                line_no=i,
                product_id=line["product_id"],
                product_version_id=version_id,
                material_id=line.get("material_id"),
                qty=line["qty"],
                qty_shipped=Decimal("0"),
                unit=line.get("unit", "PCS"),
                required_date=line.get("required_date") or required_date,
                remark=line.get("remark"),
                created_by=self.operator,
            )
            self.db.add(sl)
        await self.db.flush()
        return so

    async def confirm_sales_order(self, order_id: int) -> SalesOrder:
        so = await self.db.get(SalesOrder, order_id)
        if not so:
            raise PlanningError("销售订单不存在")
        if so.status != "DRAFT":
            raise PlanningError(f"当前状态不可确认: {so.status}")
        so.status = "CONFIRMED"
        return so

    async def _latest_released_version(self, product_id: int) -> Optional[int]:
        result = await self.db.execute(
            select(ProductVersion)
            .where(
                ProductVersion.product_id == product_id,
                ProductVersion.status == "RELEASED",
            )
            .order_by(ProductVersion.id.desc())
            .limit(1)
        )
        v = result.scalar_one_or_none()
        return v.id if v else None

    # ---------- 库存 / 在途 ----------
    async def _available_qty(self, material_id: int) -> tuple[Decimal, Decimal]:
        """返回 (on_hand, reserved) 全仓库汇总"""
        result = await self.db.execute(
            select(
                func.coalesce(func.sum(StockBalance.qty), 0),
                func.coalesce(func.sum(StockBalance.qty_reserved), 0),
            ).where(StockBalance.material_id == material_id)
        )
        row = result.one()
        return Decimal(str(row[0])), Decimal(str(row[1]))

    async def _on_order_qty(self, material_id: int) -> Decimal:
        """在途：已确认/部分到货 PO 中未收完数量"""
        result = await self.db.execute(
            select(
                func.coalesce(
                    func.sum(PurchaseOrderLine.qty - PurchaseOrderLine.qty_received),
                    0,
                )
            )
            .join(PurchaseOrder, PurchaseOrder.id == PurchaseOrderLine.order_id)
            .where(
                PurchaseOrderLine.material_id == material_id,
                PurchaseOrder.status.in_(["CONFIRMED", "PARTIAL"]),
            )
        )
        return Decimal(str(result.scalar_one()))

    # ---------- 多级 BOM 展开 ----------
    async def explode_bom(
        self,
        product_version_id: int,
        order_qty: Decimal,
        max_level: int = 10,
    ) -> list[dict]:
        """
        多级 BOM 展开。
        返回 [{material_id, level, gross_qty, parent_material_id, qty_per, scrap_rate}, ...]
        """
        results: list[dict] = []

        async def _explode(version_id: int, qty: Decimal, level: int, parent_mat: Optional[int]):
            if level > max_level:
                return
            bom = (
                await self.db.execute(
                    select(BomHeader).where(
                        BomHeader.product_version_id == version_id
                    )
                )
            ).scalar_one_or_none()
            if not bom:
                return

            lines = (
                await self.db.execute(
                    select(BomLine)
                    .where(BomLine.bom_id == bom.id, BomLine.is_alternative == False)
                    .order_by(BomLine.line_no)
                )
            ).scalars().all()

            for line in lines:
                gross = qty * line.qty_per * (Decimal("1") + (line.scrap_rate or Decimal("0")))
                results.append({
                    "material_id": line.material_id,
                    "level": level,
                    "gross_qty": gross,
                    "parent_material_id": parent_mat,
                    "qty_per": line.qty_per,
                    "scrap_rate": line.scrap_rate or Decimal("0"),
                })
                # 若该物料是半成品（有对应产品版本），继续展开
                # 简化：查找 material 关联的 product 的最新 RELEASED 版本
                child_version = await self._material_as_product_version(line.material_id)
                if child_version:
                    await _explode(child_version, gross, level + 1, line.material_id)

        await _explode(product_version_id, order_qty, 1, None)
        return results

    async def _material_as_product_version(self, material_id: int) -> Optional[int]:
        """物料若对应某产品（product.material_id），返回其最新已发布版本"""
        product = (
            await self.db.execute(
                select(Product).where(Product.material_id == material_id)
            )
        ).scalar_one_or_none()
        if not product:
            return None
        return await self._latest_released_version(product.id)

    # ---------- 跑 MRP ----------
    async def run_mrp(
        self,
        sales_order_id: Optional[int] = None,
        remark: Optional[str] = None,
    ) -> MrpRun:
        """
        对指定销售订单（或全部已确认订单）跑 MRP。
        """
        run_no = await generate_document_number(self.db, "MRP")
        run = MrpRun(
            run_no=run_no,
            status="RUNNING",
            sales_order_id=sales_order_id,
            remark=remark,
            created_by=self.operator,
        )
        self.db.add(run)
        await self.db.flush()

        # 收集订单行
        if sales_order_id:
            so = await self.db.get(SalesOrder, sales_order_id)
            if not so or so.status not in ("CONFIRMED", "PARTIAL"):
                run.status = "FAILED"
                raise PlanningError("销售订单不存在或未确认")
            lines = (
                await self.db.execute(
                    select(SalesOrderLine).where(SalesOrderLine.order_id == sales_order_id)
                )
            ).scalars().all()
        else:
            result = await self.db.execute(
                select(SalesOrderLine)
                .join(SalesOrder, SalesOrder.id == SalesOrderLine.order_id)
                .where(SalesOrder.status.in_(["CONFIRMED", "PARTIAL"]))
            )
            lines = result.scalars().all()

        if not lines:
            run.status = "DONE"
            return run

        # 汇总毛需求 material_id -> gross
        gross_map: dict[int, dict] = defaultdict(
            lambda: {"gross": Decimal("0"), "level": 99, "parent": None}
        )

        for line in lines:
            version_id = line.product_version_id
            if not version_id:
                version_id = await self._latest_released_version(line.product_id)
            if not version_id:
                continue

            # 成品自身也记一笔（level 0），便于生产建议
            product = await self.db.get(Product, line.product_id)
            if product and product.material_id:
                mid = product.material_id
                gross_map[mid]["gross"] += line.qty
                gross_map[mid]["level"] = min(gross_map[mid]["level"], 0)
                gross_map[mid]["source"] = so.doc_no if sales_order_id else "MULTI"
            elif line.material_id:
                gross_map[line.material_id]["gross"] += line.qty
                gross_map[line.material_id]["level"] = min(
                    gross_map[line.material_id]["level"], 0
                )

            exploded = await self.explode_bom(version_id, line.qty)
            for item in exploded:
                mid = item["material_id"]
                gross_map[mid]["gross"] += item["gross_qty"]
                gross_map[mid]["level"] = min(gross_map[mid]["level"], item["level"])
                gross_map[mid]["parent"] = item.get("parent_material_id")

        # 计算净需求并写明细
        for material_id, info in gross_map.items():
            on_hand, reserved = await self._available_qty(material_id)
            on_order = await self._on_order_qty(material_id)
            available = on_hand - reserved
            net = info["gross"] - available - on_order
            if net < 0:
                net = Decimal("0")

            # 建议类型：看物料类型
            mat = await self.db.get(Material, material_id)
            mat_type = mat.material_type if mat else "RAW"
            if net <= 0:
                sugg_type = "NONE"
                sugg_qty = Decimal("0")
            elif mat_type in ("RAW", "CONSUMABLE"):
                sugg_type = "PURCHASE"
                sugg_qty = net
            else:
                sugg_type = "PRODUCE"
                sugg_qty = net

            req = MrpRequirement(
                run_id=run.id,
                material_id=material_id,
                level=info["level"] if info["level"] != 99 else 0,
                gross_qty=info["gross"],
                on_hand_qty=on_hand,
                reserved_qty=reserved,
                on_order_qty=on_order,
                net_qty=net,
                suggestion_type=sugg_type,
                suggestion_qty=sugg_qty,
                source_type="SO",
                source_id=info.get("source"),
                parent_material_id=info.get("parent"),
                created_by=self.operator,
            )
            self.db.add(req)

        run.status = "DONE"
        await self.db.flush()
        return run

    async def get_run_requirements(self, run_id: int) -> list[MrpRequirement]:
        result = await self.db.execute(
            select(MrpRequirement)
            .where(MrpRequirement.run_id == run_id)
            .order_by(MrpRequirement.level, MrpRequirement.material_id)
        )
        return list(result.scalars().all())

    async def create_work_orders_from_mrp(
        self,
        run_id: int,
        warehouse_id: Optional[int] = None,
        fg_warehouse_id: Optional[int] = None,
        wip_warehouse_id: Optional[int] = None,
        only_produce: bool = True,
    ) -> list:
        """根据 MRP 运行中的 PRODUCE 建议生成生产工单

        通过 material_id → Product.material_id 反查产品，取最新 RELEASED 版本。
        """
        from app.models.engineering import Product, ProductVersion
        from app.services.production import ProductionService, ProductionError

        run = await self.db.get(MrpRun, run_id)
        if not run:
            raise PlanningError("MRP 运行不存在")
        if run.status != "DONE":
            raise PlanningError(f"MRP 未完成: {run.status}")

        reqs = await self.get_run_requirements(run_id)
        produce_reqs = [
            r for r in reqs
            if (not only_produce or r.suggestion_type == "PRODUCE")
            and r.suggestion_qty > 0
        ]
        if not produce_reqs:
            raise PlanningError("没有可生成工单的生产建议")

        prod_svc = ProductionService(self.db, self.operator)
        created = []
        errors = []

        for req in produce_reqs:
            product = (
                await self.db.execute(
                    select(Product).where(Product.material_id == req.material_id)
                )
            ).scalar_one_or_none()
            if not product:
                errors.append(f"物料{req.material_id}无对应产品档案")
                continue
            version_id = await self._latest_released_version(product.id)
            if not version_id:
                errors.append(f"产品{product.code}无已发布版本")
                continue
            try:
                wo = await prod_svc.create_work_order(
                    product_id=product.id,
                    product_version_id=version_id,
                    plan_qty=req.suggestion_qty,
                    warehouse_id=warehouse_id,
                    fg_warehouse_id=fg_warehouse_id,
                    wip_warehouse_id=wip_warehouse_id,
                    sales_order_id=run.sales_order_id,
                    remark=f"来源MRP {run.run_no} 物料{req.material_id}",
                )
                created.append(wo)
            except ProductionError as e:
                errors.append(f"产品{product.code}: {e}")

        if not created and errors:
            raise PlanningError("; ".join(errors))
        return created

    async def create_purchase_orders_from_mrp(
        self,
        run_id: int,
        supplier_id: Optional[int] = None,
        order_date: Optional[date] = None,
        auto_confirm: bool = False,
        split_by_default_supplier: bool = True,
    ) -> list:
        """根据 MRP PURCHASE 建议生成采购订单

        - 若 split_by_default_supplier=True：按物料默认供应商拆成多张 PO
        - 无默认供应商的物料：落到 supplier_id（必填兜底）或报错
        - 若 split=False：全部合并到 supplier_id 一张 PO
        """
        from collections import defaultdict
        from app.models.master_data import MaterialSupplier
        from app.services.purchase import PurchaseService, PurchaseError

        run = await self.db.get(MrpRun, run_id)
        if not run:
            raise PlanningError("MRP 运行不存在")
        if run.status != "DONE":
            raise PlanningError(f"MRP 未完成: {run.status}")

        reqs = await self.get_run_requirements(run_id)
        purchase_reqs = [
            r for r in reqs
            if r.suggestion_type == "PURCHASE" and r.suggestion_qty > 0
        ]
        if not purchase_reqs:
            raise PlanningError("没有可生成采购订单的采购建议")

        # material_id -> supplier_id
        groups: dict[int, list] = defaultdict(list)

        if split_by_default_supplier:
            for r in purchase_reqs:
                pref = (
                    await self.db.execute(
                        select(MaterialSupplier)
                        .where(
                            MaterialSupplier.material_id == r.material_id,
                            MaterialSupplier.is_default == True,
                        )
                        .limit(1)
                    )
                ).scalar_one_or_none()
                sid = pref.supplier_id if pref else supplier_id
                if not sid:
                    raise PlanningError(
                        f"物料 {r.material_id} 无默认供应商，请指定 supplier_id 或维护物料供应商"
                    )
                groups[sid].append(r)
        else:
            if not supplier_id:
                raise PlanningError("未拆分模式下必须指定 supplier_id")
            groups[supplier_id] = purchase_reqs

        purchase = PurchaseService(self.db, self.operator)
        created = []
        try:
            for sid, req_list in groups.items():
                lines = [
                    {
                        "material_id": r.material_id,
                        "qty": r.suggestion_qty,
                        "unit": "PCS",
                        "remark": f"MRP {run.run_no} net={r.net_qty}",
                    }
                    for r in req_list
                ]
                po = await purchase.create_order(
                    supplier_id=sid,
                    order_date=order_date or date.today(),
                    lines=lines,
                    remark=f"来源MRP {run.run_no}",
                )
                if auto_confirm:
                    po = await purchase.confirm_order(po.id)
                created.append(po)
        except PurchaseError as e:
            raise PlanningError(str(e)) from e
        return created

