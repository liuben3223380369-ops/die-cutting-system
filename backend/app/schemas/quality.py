"""质量 / 成本 Schema"""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class DefectCreate(BaseModel):
    code: str
    name: str
    category: str = "GENERAL"


class DefectOut(BaseModel):
    id: int
    code: str
    name: str
    category: str
    is_active: bool

    model_config = {"from_attributes": True}


class InspectionCreate(BaseModel):
    inspect_type: str = Field(..., pattern="^(IPQC|FQC)$")
    result: str = Field(..., pattern="^(PASSED|FAILED|PARTIAL)$")
    qty_inspected: Decimal = Field(..., gt=0)
    qty_passed: Decimal = Field(..., ge=0)
    qty_failed: Decimal = Field(..., ge=0)
    inspect_date: date
    material_id: Optional[int] = None
    work_order_id: Optional[int] = None
    operation_id: Optional[int] = None
    batch_no: str = ""
    defect_codes: Optional[str] = None
    inspector: Optional[str] = None
    remark: Optional[str] = None


class InspectionOut(BaseModel):
    id: int
    doc_no: str
    inspect_type: str
    result: str
    material_id: Optional[int]
    work_order_id: Optional[int]
    batch_no: str
    qty_inspected: Decimal
    qty_passed: Decimal
    qty_failed: Decimal
    defect_codes: Optional[str]
    inspector: Optional[str]
    inspect_date: date
    created_at: datetime

    model_config = {"from_attributes": True}


class QualityIssueCreate(BaseModel):
    issue_type: str = "DEFECT"
    qty: Decimal = Field(..., ge=0)
    material_id: Optional[int] = None
    work_order_id: Optional[int] = None
    batch_no: str = ""
    defect_codes: Optional[str] = None
    description: Optional[str] = None
    warehouse_id: Optional[int] = None
    remark: Optional[str] = None


class QualityIssueOut(BaseModel):
    id: int
    doc_no: str
    status: str
    issue_type: str
    material_id: Optional[int]
    work_order_id: Optional[int]
    batch_no: str
    qty: Decimal
    defect_codes: Optional[str]
    description: Optional[str]
    disposition: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class DisposeRequest(BaseModel):
    disposition: str = Field(..., pattern="^(REWORK|SCRAP|USE_AS_IS|RETURN)$")
    hold_warehouse_id: Optional[int] = None


class TraceForwardRequest(BaseModel):
    material_id: int
    batch_no: str = ""


class TraceReverseRequest(BaseModel):
    source_type: str
    source_id: str


class StandardCostSet(BaseModel):
    material_id: int
    unit_cost: Decimal = Field(..., ge=0)
    currency: str = "CNY"
    remark: Optional[str] = None


class WorkOrderCostOut(BaseModel):
    id: int
    work_order_id: int
    material_cost: Decimal
    scrap_cost: Decimal
    mold_cost: Decimal
    process_cost: Decimal
    total_cost: Decimal
    completed_qty: Decimal
    unit_cost: Decimal
    currency: str

    model_config = {"from_attributes": True}
