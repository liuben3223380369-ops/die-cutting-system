"""计划 / MRP Schema"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class SOLineCreate(BaseModel):
    product_id: int
    product_version_id: Optional[int] = None
    material_id: Optional[int] = None
    qty: Decimal = Field(..., gt=0)
    unit: str = "PCS"
    required_date: Optional[date] = None
    remark: Optional[str] = None


class SalesOrderCreate(BaseModel):
    customer_id: int
    order_date: date
    required_date: Optional[date] = None
    remark: Optional[str] = None
    lines: List[SOLineCreate] = Field(..., min_length=1)


class SOLineOut(BaseModel):
    id: int
    line_no: int
    product_id: int
    product_version_id: Optional[int]
    material_id: Optional[int]
    qty: Decimal
    qty_shipped: Decimal
    unit: str
    required_date: Optional[date]
    remark: Optional[str]

    model_config = {"from_attributes": True}


class SalesOrderOut(BaseModel):
    id: int
    doc_no: str
    status: str
    customer_id: int
    order_date: date
    required_date: Optional[date]
    remark: Optional[str]
    created_at: datetime
    lines: List[SOLineOut] = []

    model_config = {"from_attributes": True}


class MrpRunRequest(BaseModel):
    sales_order_id: Optional[int] = None
    remark: Optional[str] = None


class MrpRequirementOut(BaseModel):
    id: int
    run_id: int
    material_id: int
    level: int
    gross_qty: Decimal
    on_hand_qty: Decimal
    reserved_qty: Decimal
    on_order_qty: Decimal
    net_qty: Decimal
    suggestion_type: str
    suggestion_qty: Decimal
    source_type: Optional[str]
    source_id: Optional[str]
    parent_material_id: Optional[int]

    model_config = {"from_attributes": True}


class MrpRunOut(BaseModel):
    id: int
    run_no: str
    status: str
    sales_order_id: Optional[int]
    remark: Optional[str]
    created_at: datetime
    requirements: List[MrpRequirementOut] = []

    model_config = {"from_attributes": True}
