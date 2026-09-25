"""基础数据 CRUD API"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.master_data import (
    MaterialSupplier,
    Customer,
    Location,
    Material,
    Supplier,
    Unit,
    Warehouse,
)
from app.schemas.common import APIResponse
from app.schemas.master_data import (
    LocationCreate,
    LocationOut,
    MaterialCreate,
    MaterialOut,
    MaterialUpdate,
    SupplierCreate,
    SupplierOut,
    UnitCreate,
    UnitOut,
    WarehouseCreate,
    WarehouseOut,
)

router = APIRouter(prefix="/master", tags=["基础数据"])


# ---------- Unit ----------
@router.post("/units", response_model=APIResponse[UnitOut])
async def create_unit(body: UnitCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Unit).where(Unit.code == body.code))
    if exists.scalar_one_or_none():
        raise HTTPException(400, f"单位编码已存在: {body.code}")
    obj = Unit(**body.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return APIResponse(data=UnitOut.model_validate(obj))


@router.get("/units", response_model=APIResponse[List[UnitOut]])
async def list_units(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Unit).where(Unit.is_active == True))
    items = result.scalars().all()
    return APIResponse(data=[UnitOut.model_validate(i) for i in items])


# ---------- Material ----------
@router.post("/materials", response_model=APIResponse[MaterialOut])
async def create_material(body: MaterialCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Material).where(Material.code == body.code))
    if exists.scalar_one_or_none():
        raise HTTPException(400, f"物料编码已存在: {body.code}")
    obj = Material(**body.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return APIResponse(data=MaterialOut.model_validate(obj))


@router.get("/materials", response_model=APIResponse[List[MaterialOut]])
async def list_materials(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Material)
    if active_only:
        stmt = stmt.where(Material.is_active == True)
    result = await db.execute(stmt.order_by(Material.code))
    items = result.scalars().all()
    return APIResponse(data=[MaterialOut.model_validate(i) for i in items])


@router.get("/materials/{material_id}", response_model=APIResponse[MaterialOut])
async def get_material(material_id: int, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Material, material_id)
    if not obj:
        raise HTTPException(404, "物料不存在")
    return APIResponse(data=MaterialOut.model_validate(obj))


@router.patch("/materials/{material_id}", response_model=APIResponse[MaterialOut])
async def update_material(
    material_id: int,
    body: MaterialUpdate,
    db: AsyncSession = Depends(get_db),
):
    obj = await db.get(Material, material_id)
    if not obj:
        raise HTTPException(404, "物料不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    await db.flush()
    await db.refresh(obj)
    return APIResponse(data=MaterialOut.model_validate(obj))


# ---------- Supplier ----------
@router.post("/suppliers", response_model=APIResponse[SupplierOut])
async def create_supplier(body: SupplierCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Supplier).where(Supplier.code == body.code))
    if exists.scalar_one_or_none():
        raise HTTPException(400, f"供应商编码已存在: {body.code}")
    obj = Supplier(**body.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return APIResponse(data=SupplierOut.model_validate(obj))


@router.get("/suppliers", response_model=APIResponse[List[SupplierOut]])
async def list_suppliers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Supplier).where(Supplier.is_active == True).order_by(Supplier.code)
    )
    items = result.scalars().all()
    return APIResponse(data=[SupplierOut.model_validate(i) for i in items])


# ---------- Warehouse ----------
@router.post("/warehouses", response_model=APIResponse[WarehouseOut])
async def create_warehouse(body: WarehouseCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Warehouse).where(Warehouse.code == body.code))
    if exists.scalar_one_or_none():
        raise HTTPException(400, f"仓库编码已存在: {body.code}")
    obj = Warehouse(**body.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return APIResponse(data=WarehouseOut.model_validate(obj))


@router.get("/warehouses", response_model=APIResponse[List[WarehouseOut]])
async def list_warehouses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Warehouse).where(Warehouse.is_active == True).order_by(Warehouse.code)
    )
    items = result.scalars().all()
    return APIResponse(data=[WarehouseOut.model_validate(i) for i in items])


# ---------- Location ----------
@router.post("/locations", response_model=APIResponse[LocationOut])
async def create_location(body: LocationCreate, db: AsyncSession = Depends(get_db)):
    wh = await db.get(Warehouse, body.warehouse_id)
    if not wh:
        raise HTTPException(400, "仓库不存在")
    obj = Location(**body.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return APIResponse(data=LocationOut.model_validate(obj))


@router.get("/locations", response_model=APIResponse[List[LocationOut]])
async def list_locations(
    warehouse_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Location).where(Location.is_active == True)
    if warehouse_id:
        stmt = stmt.where(Location.warehouse_id == warehouse_id)
    result = await db.execute(stmt.order_by(Location.code))
    items = result.scalars().all()
    return APIResponse(data=[LocationOut.model_validate(i) for i in items])


# ---------- Customer ----------
from pydantic import BaseModel as _BM

class _CustomerCreate(_BM):
    code: str
    name: str
    contact: str | None = None
    phone: str | None = None


@router.post("/customers")
async def create_customer(body: _CustomerCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(select(Customer).where(Customer.code == body.code))
    if exists.scalar_one_or_none():
        raise HTTPException(400, f"客户编码已存在: {body.code}")
    obj = Customer(**body.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return APIResponse(data={"id": obj.id, "code": obj.code, "name": obj.name, "is_active": obj.is_active})


@router.get("/customers")
async def list_customers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Customer).where(Customer.is_active == True).order_by(Customer.code)
    )
    items = result.scalars().all()
    return APIResponse(
        data=[{"id": i.id, "code": i.code, "name": i.name, "is_active": i.is_active} for i in items]
    )


# ---------- Material default supplier ----------
class _MatSupCreate(_BM):
    material_id: int
    supplier_id: int
    is_default: bool = True
    lead_time_days: int | None = None
    remark: str | None = None


@router.post("/material-suppliers")
async def create_material_supplier(body: _MatSupCreate, db: AsyncSession = Depends(get_db)):
    exists = await db.execute(
        select(MaterialSupplier).where(
            MaterialSupplier.material_id == body.material_id,
            MaterialSupplier.supplier_id == body.supplier_id,
        )
    )
    if exists.scalar_one_or_none():
        raise HTTPException(400, "该物料-供应商关系已存在")
    if body.is_default:
        # 取消同物料其他默认
        others = (
            await db.execute(
                select(MaterialSupplier).where(
                    MaterialSupplier.material_id == body.material_id,
                    MaterialSupplier.is_default == True,
                )
            )
        ).scalars().all()
        for o in others:
            o.is_default = False
    obj = MaterialSupplier(**body.model_dump())
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return APIResponse(
        data={
            "id": obj.id,
            "material_id": obj.material_id,
            "supplier_id": obj.supplier_id,
            "is_default": obj.is_default,
            "lead_time_days": obj.lead_time_days,
        }
    )


@router.get("/material-suppliers")
async def list_material_suppliers(
    material_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(MaterialSupplier).order_by(MaterialSupplier.material_id)
    if material_id:
        stmt = stmt.where(MaterialSupplier.material_id == material_id)
    items = (await db.execute(stmt.limit(200))).scalars().all()
    return APIResponse(
        data=[
            {
                "id": i.id,
                "material_id": i.material_id,
                "supplier_id": i.supplier_id,
                "is_default": i.is_default,
                "lead_time_days": i.lead_time_days,
            }
            for i in items
        ]
    )
