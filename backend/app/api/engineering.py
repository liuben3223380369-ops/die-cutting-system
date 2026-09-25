"""工程模块 API"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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
from app.schemas.common import APIResponse
from app.schemas.engineering import (
    BomOut,
    BomLineOut,
    BomSaveRequest,
    MoldCreate,
    MoldOut,
    NestingCreate,
    NestingOut,
    ProcessStepOut,
    ProductCreate,
    ProductOut,
    ProductVersionCreate,
    ProductVersionOut,
    RouteOut,
    RouteSaveRequest,
)
from app.services.engineering import (
    EngineeringError,
    EngineeringService,
    VersionFrozenError,
)

router = APIRouter(prefix="/engineering", tags=["工程"])


# ---------- Product ----------
@router.post("/products", response_model=APIResponse[ProductOut])
async def create_product(body: ProductCreate, db: AsyncSession = Depends(get_db)):
    svc = EngineeringService(db)
    try:
        obj = await svc.create_product(**body.model_dump())
        return APIResponse(data=ProductOut.model_validate(obj))
    except EngineeringError as e:
        raise HTTPException(400, str(e))


@router.get("/products", response_model=APIResponse[List[ProductOut]])
async def list_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Product).where(Product.is_active == True).order_by(Product.code)
    )
    return APIResponse(data=[ProductOut.model_validate(i) for i in result.scalars().all()])


@router.get("/products/{product_id}", response_model=APIResponse[ProductOut])
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    obj = await db.get(Product, product_id)
    if not obj:
        raise HTTPException(404, "产品不存在")
    return APIResponse(data=ProductOut.model_validate(obj))


# ---------- Version ----------
@router.post("/versions", response_model=APIResponse[ProductVersionOut])
async def create_version(body: ProductVersionCreate, db: AsyncSession = Depends(get_db)):
    svc = EngineeringService(db)
    try:
        obj = await svc.create_version(**body.model_dump())
        return APIResponse(data=ProductVersionOut.model_validate(obj))
    except EngineeringError as e:
        raise HTTPException(400, str(e))


@router.get("/versions", response_model=APIResponse[List[ProductVersionOut]])
async def list_versions(
    product_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ProductVersion).order_by(ProductVersion.id.desc())
    if product_id:
        stmt = stmt.where(ProductVersion.product_id == product_id)
    result = await db.execute(stmt.limit(100))
    return APIResponse(
        data=[ProductVersionOut.model_validate(i) for i in result.scalars().all()]
    )


@router.post("/versions/{version_id}/release", response_model=APIResponse[ProductVersionOut])
async def release_version(version_id: int, db: AsyncSession = Depends(get_db)):
    svc = EngineeringService(db)
    try:
        obj = await svc.release_version(version_id)
        return APIResponse(data=ProductVersionOut.model_validate(obj))
    except (EngineeringError, VersionFrozenError) as e:
        raise HTTPException(400, str(e))


# ---------- BOM ----------
@router.post("/bom", response_model=APIResponse[BomOut])
async def save_bom(body: BomSaveRequest, db: AsyncSession = Depends(get_db)):
    svc = EngineeringService(db)
    try:
        bom = await svc.save_bom(
            product_version_id=body.product_version_id,
            lines=[l.model_dump() for l in body.lines],
            remark=body.remark,
        )
        lines = (
            await db.execute(select(BomLine).where(BomLine.bom_id == bom.id))
        ).scalars().all()
        out = BomOut(
            id=bom.id,
            product_version_id=bom.product_version_id,
            status=bom.status,
            remark=bom.remark,
            lines=[BomLineOut.model_validate(l) for l in lines],
        )
        return APIResponse(data=out)
    except VersionFrozenError as e:
        raise HTTPException(409, str(e))
    except EngineeringError as e:
        raise HTTPException(400, str(e))


@router.get("/bom/{product_version_id}", response_model=APIResponse[BomOut])
async def get_bom(product_version_id: int, db: AsyncSession = Depends(get_db)):
    bom = (
        await db.execute(
            select(BomHeader).where(BomHeader.product_version_id == product_version_id)
        )
    ).scalar_one_or_none()
    if not bom:
        raise HTTPException(404, "BOM 不存在")
    lines = (
        await db.execute(select(BomLine).where(BomLine.bom_id == bom.id))
    ).scalars().all()
    return APIResponse(
        data=BomOut(
            id=bom.id,
            product_version_id=bom.product_version_id,
            status=bom.status,
            remark=bom.remark,
            lines=[BomLineOut.model_validate(l) for l in lines],
        )
    )


# ---------- Route ----------
@router.post("/routes", response_model=APIResponse[RouteOut])
async def save_route(body: RouteSaveRequest, db: AsyncSession = Depends(get_db)):
    svc = EngineeringService(db)
    try:
        route = await svc.save_route(
            product_version_id=body.product_version_id,
            steps=[s.model_dump() for s in body.steps],
            remark=body.remark,
        )
        steps = (
            await db.execute(
                select(ProcessStep)
                .where(ProcessStep.route_id == route.id)
                .order_by(ProcessStep.seq)
            )
        ).scalars().all()
        return APIResponse(
            data=RouteOut(
                id=route.id,
                product_version_id=route.product_version_id,
                status=route.status,
                remark=route.remark,
                steps=[ProcessStepOut.model_validate(s) for s in steps],
            )
        )
    except VersionFrozenError as e:
        raise HTTPException(409, str(e))
    except EngineeringError as e:
        raise HTTPException(400, str(e))


@router.get("/routes/{product_version_id}", response_model=APIResponse[RouteOut])
async def get_route(product_version_id: int, db: AsyncSession = Depends(get_db)):
    route = (
        await db.execute(
            select(ProcessRoute).where(
                ProcessRoute.product_version_id == product_version_id
            )
        )
    ).scalar_one_or_none()
    if not route:
        raise HTTPException(404, "工艺路线不存在")
    steps = (
        await db.execute(
            select(ProcessStep)
            .where(ProcessStep.route_id == route.id)
            .order_by(ProcessStep.seq)
        )
    ).scalars().all()
    return APIResponse(
        data=RouteOut(
            id=route.id,
            product_version_id=route.product_version_id,
            status=route.status,
            remark=route.remark,
            steps=[ProcessStepOut.model_validate(s) for s in steps],
        )
    )


# ---------- Mold ----------
@router.post("/molds", response_model=APIResponse[MoldOut])
async def create_mold(body: MoldCreate, db: AsyncSession = Depends(get_db)):
    svc = EngineeringService(db)
    try:
        obj = await svc.create_mold(**body.model_dump())
        return APIResponse(data=MoldOut.model_validate(obj))
    except EngineeringError as e:
        raise HTTPException(400, str(e))


@router.get("/molds", response_model=APIResponse[List[MoldOut]])
async def list_molds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Mold).order_by(Mold.code))
    return APIResponse(data=[MoldOut.model_validate(i) for i in result.scalars().all()])


# ---------- Nesting ----------
@router.post("/nestings", response_model=APIResponse[NestingOut])
async def create_nesting(body: NestingCreate, db: AsyncSession = Depends(get_db)):
    svc = EngineeringService(db)
    try:
        obj = await svc.create_nesting(**body.model_dump())
        return APIResponse(data=NestingOut.model_validate(obj))
    except VersionFrozenError as e:
        raise HTTPException(409, str(e))
    except EngineeringError as e:
        raise HTTPException(400, str(e))


@router.get("/nestings", response_model=APIResponse[List[NestingOut]])
async def list_nestings(
    product_version_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(NestingLayout).order_by(NestingLayout.id.desc())
    if product_version_id:
        stmt = stmt.where(NestingLayout.product_version_id == product_version_id)
    result = await db.execute(stmt.limit(50))
    return APIResponse(
        data=[NestingOut.model_validate(i) for i in result.scalars().all()]
    )
