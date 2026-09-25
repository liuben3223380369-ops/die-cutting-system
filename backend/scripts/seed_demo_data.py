#!/usr/bin/env python3
"""演示数据种子 —— 一键写入可跑通全流程的主数据与样例工程

用法（在 backend 目录）:
  python scripts/seed_demo_data.py
"""
import asyncio
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# 保证可 import app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def main():
    from app.core.database import Base, engine, AsyncSessionLocal
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from app.models.master_data import Material, MaterialSupplier, Supplier, Warehouse, Customer, Unit
        from app.services.engineering import EngineeringService
        from app.services.inventory import InventoryService
        from app.models.inventory import StockSourceType
        from app.services.costing import CostingService

        # 幂等：已有物料则跳过
        exists = (
            await db.execute(select(Material).where(Material.code == "RAW-PET-50"))
        ).scalar_one_or_none()
        if exists:
            print("演示数据已存在，跳过。若需重建请清空 data/die_cutting.db")
            return

        unit = Unit(code="PCS", name="个")
        unit2 = Unit(code="M", name="米")
        db.add_all([unit, unit2])

        wh_rm = Warehouse(code="WH-RM", name="原料仓", warehouse_type="NORMAL")
        wh_fg = Warehouse(code="WH-FG", name="成品仓", warehouse_type="NORMAL")
        wh_wip = Warehouse(code="WH-WIP", name="在制品仓", warehouse_type="WIP")
        db.add_all([wh_rm, wh_fg, wh_wip])

        sup = Supplier(code="SUP-01", name="华南胶粘材料")
        cust = Customer(code="CUS-01", name="示例电子客户")
        db.add_all([sup, cust])

        raw = Material(
            code="RAW-PET-50",
            name="PET胶带 50um",
            material_type="RAW",
            base_unit="PCS",
        )
        fg = Material(
            code="FG-PAD-001",
            name="模切垫片成品",
            material_type="FG",
            base_unit="PCS",
        )
        db.add_all([raw, fg])
        await db.flush()

        eng = EngineeringService(db, operator="seed")
        product = await eng.create_product(
            code="PRD-PAD-001",
            name="模切垫片",
            material_id=fg.id,
            customer_id=cust.id,
            customer_part_no="CUS-PN-001",
        )
        ver = await eng.create_version(product.id, "V1", drawing_no="DWG-001", drawing_rev="A")
        await eng.save_bom(
            ver.id,
            lines=[
                {
                    "material_id": raw.id,
                    "qty_per": Decimal("1.2"),
                    "scrap_rate": Decimal("0.05"),
                    "unit": "PCS",
                }
            ],
        )
        await eng.save_route(
            ver.id,
            steps=[
                {"seq": 10, "step_code": "SLIT", "step_name": "分条", "step_type": "SLITTING"},
                {"seq": 20, "step_code": "DIE", "step_name": "模切", "step_type": "DIE_CUTTING"},
                {"seq": 30, "step_code": "WASTE", "step_name": "排废", "step_type": "WASTE"},
            ],
        )
        await eng.release_version(ver.id)

        inv = InventoryService(db, operator="seed")
        await inv.stock_in(
            source_type=StockSourceType.PURCHASE_IN,
            source_id="SEED-PO",
            material_id=raw.id,
            warehouse_id=wh_rm.id,
            qty=Decimal("5000"),
            batch_no="BATCH-SEED-01",
            remark="演示初始库存",
        )

        cost = CostingService(db, operator="seed")
        await cost.set_standard_cost(raw.id, Decimal("0.35"))
        await cost.set_standard_cost(fg.id, Decimal("2.50"))

        ms = MaterialSupplier(
            material_id=raw.id,
            supplier_id=sup.id,
            is_default=True,
            lead_time_days=7,
        )
        db.add(ms)

        await db.commit()
        print("演示数据写入成功：")
        print(f"  原料 {raw.code} id={raw.id} 库存 5000 @ {wh_rm.code}")
        print(f"  成品 {fg.code} id={fg.id}")
        print(f"  产品 {product.code} 版本 V1 RELEASED")
        print(f"  仓库 RM={wh_rm.id} FG={wh_fg.id} WIP={wh_wip.id}")
        print("可直接：建销售订单 / 跑 MRP / 建工单领料生产")


if __name__ == "__main__":
    asyncio.run(main())
