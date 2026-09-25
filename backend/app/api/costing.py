"""成本 API"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.costing import MaterialStandardCost, WorkOrderCost
from app.schemas.common import APIResponse
from app.schemas.quality import StandardCostSet, WorkOrderCostOut
from app.services.costing import CostingError, CostingService

router = APIRouter(prefix="/costing", tags=["成本"])


@router.post("/standard-costs", response_model=APIResponse[dict])
async def set_standard_cost(body: StandardCostSet, db: AsyncSession = Depends(get_db)):
    svc = CostingService(db)
    obj = await svc.set_standard_cost(**body.model_dump())
    return APIResponse(
        data={
            "id": obj.id,
            "material_id": obj.material_id,
            "unit_cost": str(obj.unit_cost),
            "currency": obj.currency,
        }
    )


@router.get("/standard-costs", response_model=APIResponse[List[dict]])
async def list_standard_costs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MaterialStandardCost).order_by(MaterialStandardCost.material_id))
    items = result.scalars().all()
    return APIResponse(
        data=[
            {
                "id": i.id,
                "material_id": i.material_id,
                "unit_cost": str(i.unit_cost),
                "currency": i.currency,
            }
            for i in items
        ]
    )


@router.post("/work-orders/{wo_id}/calculate", response_model=APIResponse[WorkOrderCostOut])
async def calculate_wo_cost(wo_id: int, db: AsyncSession = Depends(get_db)):
    svc = CostingService(db)
    try:
        obj = await svc.calculate_work_order_cost(wo_id)
        return APIResponse(data=WorkOrderCostOut.model_validate(obj))
    except CostingError as e:
        raise HTTPException(400, str(e))


@router.get("/work-orders/{wo_id}", response_model=APIResponse[WorkOrderCostOut])
async def get_wo_cost(wo_id: int, db: AsyncSession = Depends(get_db)):
    obj = (
        await db.execute(
            select(WorkOrderCost).where(WorkOrderCost.work_order_id == wo_id)
        )
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(404, "尚未计算成本，请先调用 calculate")
    return APIResponse(data=WorkOrderCostOut.model_validate(obj))
