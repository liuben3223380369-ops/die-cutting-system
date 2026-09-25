"""生产 Schema"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class WorkOrderCreate(BaseModel):
    product_id: int
    product_version_id: int
    plan_qty: Decimal = Field(..., gt=0)
    warehouse_id: Optional[int] = None
    fg_warehouse_id: Optional[int] = None
    wip_warehouse_id: Optional[int] = None
    plan_start: Optional[date] = None
    plan_end: Optional[date] = None
    sales_order_id: Optional[int] = None
    unit: str = "PCS"
    remark: Optional[str] = None


class WOMaterialOut(BaseModel):
    id: int
    material_id: int
    qty_required: Decimal
    qty_issued: Decimal
    qty_returned: Decimal
    unit: str

    model_config = {"from_attributes": True}


class WOOperationOut(BaseModel):
    id: int
    seq: int
    step_code: str
    step_name: str
    step_type: str
    mold_id: Optional[int]
    status: str
    qty_good: Decimal
    qty_reject: Decimal
    qty_scrap: Decimal

    model_config = {"from_attributes": True}


class WorkOrderOut(BaseModel):
    id: int
    doc_no: str
    status: str
    product_id: int
    product_version_id: int
    bom_id: Optional[int]
    route_id: Optional[int]
    nesting_id: Optional[int]
    plan_qty: Decimal
    completed_qty: Decimal
    scrap_qty: Decimal
    unit: str
    warehouse_id: Optional[int]
    fg_warehouse_id: Optional[int]
    wip_warehouse_id: Optional[int] = None
    plan_start: Optional[date]
    plan_end: Optional[date]
    sales_order_id: Optional[int]
    remark: Optional[str]
    created_at: datetime
    materials: List[WOMaterialOut] = []
    operations: List[WOOperationOut] = []
    progress_pct: float = 0

    model_config = {"from_attributes": True}


class IssueMaterialItem(BaseModel):
    material_id: int
    qty: Decimal = Field(..., gt=0)
    batch_no: str = ""
    roll_no: str = ""


class IssueMaterialsRequest(BaseModel):
    items: List[IssueMaterialItem] = Field(..., min_length=1)
    warehouse_id: Optional[int] = None


class ReportOperationRequest(BaseModel):
    operation_id: int
    qty_good: Decimal = Field(default=Decimal("0"), ge=0)
    qty_reject: Decimal = Field(default=Decimal("0"), ge=0)
    qty_scrap: Decimal = Field(default=Decimal("0"), ge=0)
    report_date: Optional[date] = None
    operator_name: Optional[str] = None
    downtime_min: Optional[Decimal] = None
    remark: Optional[str] = None


class ReturnMaterialsRequest(BaseModel):
    items: List[IssueMaterialItem] = Field(..., min_length=1)
    warehouse_id: Optional[int] = None


class CompleteRequest(BaseModel):
    force: bool = False


class ReceiveFGRequest(BaseModel):

    qty: Decimal = Field(..., gt=0)
    warehouse_id: Optional[int] = None
    material_id: Optional[int] = None
    batch_no: str = ""


class OperationReportOut(BaseModel):
    id: int
    doc_no: str
    work_order_id: int
    operation_id: int
    qty_good: Decimal
    qty_reject: Decimal
    qty_scrap: Decimal
    report_date: date
    operator_name: Optional[str]
    remark: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
