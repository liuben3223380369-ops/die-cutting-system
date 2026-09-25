"""采购 → 库存 → 生产 全链路测试（依赖安装后运行）

pytest tests/test_full_chain.py -v
"""
from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("sqlalchemy")
pytest.importorskip("pytest_asyncio")
pytestmark = pytest.mark.asyncio


async def test_purchase_to_stock_to_production(db_session):
    from app.models.master_data import Material, Supplier, Warehouse
    from app.models.engineering import Product, ProductVersion, BomHeader, BomLine, ProcessRoute, ProcessStep
    from app.models.inventory import StockSourceType
    from app.services.inventory import InventoryService, NegativeStockError
    from app.services.purchase import PurchaseService
    from app.services.production import ProductionService
    from app.services.engineering import EngineeringService
    from app.services.costing import CostingService
    from app.services.period import PeriodService

    db = db_session

    # --- 主数据 ---
    m_raw = Material(code="RAW1", name="原料A", material_type="RAW", base_unit="PCS")
    m_fg = Material(code="FG1", name="成品A", material_type="FG", base_unit="PCS")
    sup = Supplier(code="S1", name="供应商")
    wh = Warehouse(code="WH1", name="原料仓")
    wh_fg = Warehouse(code="FGWH", name="成品仓")
    db.add_all([m_raw, m_fg, sup, wh, wh_fg])
    await db.flush()

    # --- 工程：产品版本 BOM 工艺并发布 ---
    eng = EngineeringService(db)
    product = await eng.create_product(code="P1", name="产品1", material_id=m_fg.id)
    ver = await eng.create_version(product.id, "V1")
    await eng.save_bom(
        ver.id,
        lines=[{"material_id": m_raw.id, "qty_per": Decimal("2"), "scrap_rate": Decimal("0.1")}],
    )
    await eng.save_route(
        ver.id,
        steps=[
            {"seq": 10, "step_code": "DIE", "step_name": "模切", "step_type": "DIE_CUTTING"},
        ],
    )
    await eng.release_version(ver.id)

    # --- 采购入库路径：直接用库存服务模拟合格入库 ---
    inv = InventoryService(db)
    await inv.stock_in(
        source_type=StockSourceType.PURCHASE_IN,
        source_id="PO-TEST",
        material_id=m_raw.id,
        warehouse_id=wh.id,
        qty=Decimal("1000"),
        batch_no="B1",
    )
    avail = await inv.get_available_qty(m_raw.id, wh.id, batch_no="B1")
    assert avail == Decimal("1000")

    # --- 生产：建工单 → 下达 → 领料 → 报工 → 入库 → 完工 ---
    prod = ProductionService(db)
    wo = await prod.create_work_order(
        product_id=product.id,
        product_version_id=ver.id,
        plan_qty=Decimal("100"),
        warehouse_id=wh.id,
        fg_warehouse_id=wh_fg.id,
    )
    # 需求 = 100 * 2 * 1.1 = 220
    from sqlalchemy import select
    from app.models.production import WorkOrderMaterial, WorkOrderOperation

    mats = (
        await db.execute(
            select(WorkOrderMaterial).where(WorkOrderMaterial.work_order_id == wo.id)
        )
    ).scalars().all()
    assert len(mats) == 1
    assert mats[0].qty_required == Decimal("220.0") or mats[0].qty_required == Decimal("220")

    await prod.release_work_order(wo.id)
    await prod.issue_materials(
        wo.id,
        issues=[{"material_id": m_raw.id, "qty": Decimal("220"), "batch_no": "B1"}],
        warehouse_id=wh.id,
    )
    avail_after = await inv.get_available_qty(m_raw.id, wh.id, batch_no="B1")
    assert avail_after == Decimal("780")

    ops = (
        await db.execute(
            select(WorkOrderOperation).where(WorkOrderOperation.work_order_id == wo.id)
        )
    ).scalars().all()
    assert len(ops) == 1
    await prod.report_operation(wo.id, ops[0].id, qty_good=Decimal("100"))
    await prod.receive_fg(wo.id, qty=Decimal("100"), material_id=m_fg.id)
    await prod.complete_work_order(wo.id)

    fg_avail = await inv.get_available_qty(m_fg.id, wh_fg.id)
    assert fg_avail == Decimal("100")

    # --- 成本 ---
    cost_svc = CostingService(db)
    await cost_svc.set_standard_cost(m_raw.id, Decimal("1.5"))
    cost = await cost_svc.calculate_work_order_cost(wo.id)
    assert cost.material_cost == Decimal("330.0") or cost.material_cost == Decimal("330")  # 220*1.5
    assert cost.completed_qty == Decimal("100")
    assert cost.unit_cost > 0

    # --- 负库存拦截 ---
    with pytest.raises(NegativeStockError):
        await inv.stock_out(
            source_type=StockSourceType.PRODUCTION_ISSUE,
            source_id="WO-X",
            material_id=m_raw.id,
            warehouse_id=wh.id,
            qty=Decimal("99999"),
            batch_no="B1",
        )

    # --- 期间锁定 ---
    period = PeriodService(db)
    today = date.today()
    await period.lock_period(today.year, today.month)
    assert await period.is_locked(today) is True
    with pytest.raises(Exception):
        await period.assert_open(today)
    await period.unlock_period(today.year, today.month)
    assert await period.is_locked(today) is False
