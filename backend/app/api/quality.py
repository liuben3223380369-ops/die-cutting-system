"""质量与追溯 API"""
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.quality import DefectCode, InspectionRecord, QualityIssue
from app.schemas.common import APIResponse
from app.schemas.quality import (
    DefectCreate,
    DefectOut,
    DisposeRequest,
    InspectionCreate,
    InspectionOut,
    QualityIssueCreate,
    QualityIssueOut,
    TraceForwardRequest,
    TraceReverseRequest,
)
from app.services.quality import QualityError, QualityService

router = APIRouter(prefix="/quality", tags=["质量追溯"])


@router.post("/defects", response_model=APIResponse[DefectOut])
async def create_defect(body: DefectCreate, db: AsyncSession = Depends(get_db)):
    svc = QualityService(db)
    try:
        obj = await svc.create_defect(**body.model_dump())
        return APIResponse(data=DefectOut.model_validate(obj))
    except QualityError as e:
        raise HTTPException(400, str(e))


@router.get("/defects", response_model=APIResponse[List[DefectOut]])
async def list_defects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DefectCode).where(DefectCode.is_active == True).order_by(DefectCode.code)
    )
    return APIResponse(data=[DefectOut.model_validate(i) for i in result.scalars().all()])


@router.post("/inspections", response_model=APIResponse[InspectionOut])
async def create_inspection(body: InspectionCreate, db: AsyncSession = Depends(get_db)):
    svc = QualityService(db)
    try:
        obj = await svc.create_inspection(**body.model_dump())
        return APIResponse(data=InspectionOut.model_validate(obj))
    except QualityError as e:
        raise HTTPException(400, str(e))


@router.get("/inspections", response_model=APIResponse[List[InspectionOut]])
async def list_inspections(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(InspectionRecord).order_by(InspectionRecord.id.desc()).limit(50)
    )
    return APIResponse(
        data=[InspectionOut.model_validate(i) for i in result.scalars().all()]
    )


@router.post("/issues", response_model=APIResponse[QualityIssueOut])
async def create_issue(body: QualityIssueCreate, db: AsyncSession = Depends(get_db)):
    svc = QualityService(db)
    try:
        obj = await svc.create_issue(**body.model_dump())
        return APIResponse(data=QualityIssueOut.model_validate(obj))
    except QualityError as e:
        raise HTTPException(400, str(e))


@router.get("/issues", response_model=APIResponse[List[QualityIssueOut]])
async def list_issues(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(QualityIssue).order_by(QualityIssue.id.desc()).limit(50)
    )
    return APIResponse(
        data=[QualityIssueOut.model_validate(i) for i in result.scalars().all()]
    )


@router.post("/issues/{issue_id}/dispose", response_model=APIResponse[QualityIssueOut])
async def dispose_issue(
    issue_id: int, body: DisposeRequest, db: AsyncSession = Depends(get_db)
):
    svc = QualityService(db)
    try:
        obj = await svc.dispose_issue(
            issue_id, body.disposition, body.hold_warehouse_id
        )
        return APIResponse(data=QualityIssueOut.model_validate(obj))
    except QualityError as e:
        raise HTTPException(400, str(e))


@router.post("/trace/forward", response_model=APIResponse[Any])
async def forward_trace(body: TraceForwardRequest, db: AsyncSession = Depends(get_db)):
    svc = QualityService(db)
    data = await svc.forward_trace(body.material_id, body.batch_no)
    return APIResponse(data=data)


@router.post("/trace/reverse", response_model=APIResponse[Any])
async def reverse_trace(body: TraceReverseRequest, db: AsyncSession = Depends(get_db)):
    svc = QualityService(db)
    data = await svc.reverse_trace(body.source_type, body.source_id)
    return APIResponse(data=data)
