"""工程模块 Schema"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- Product ----------
class ProductCreate(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    customer_id: Optional[int] = None
    customer_part_no: Optional[str] = None
    material_id: Optional[int] = None
    remark: Optional[str] = None


class ProductOut(BaseModel):
    id: int
    code: str
    name: str
    customer_id: Optional[int]
    customer_part_no: Optional[str]
    material_id: Optional[int]
    is_active: bool
    remark: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- ProductVersion ----------
class ProductVersionCreate(BaseModel):
    product_id: int
    version_code: str = Field(..., max_length=32)
    drawing_no: Optional[str] = None
    drawing_rev: Optional[str] = None
    remark: Optional[str] = None


class ProductVersionOut(BaseModel):
    id: int
    product_id: int
    version_code: str
    status: str
    drawing_no: Optional[str]
    drawing_rev: Optional[str]
    released_at: Optional[datetime]
    remark: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- BOM ----------
class BomLineCreate(BaseModel):
    material_id: int
    qty_per: Decimal = Field(..., gt=0)
    unit: str = "PCS"
    scrap_rate: Decimal = Field(default=Decimal("0"), ge=0)
    is_alternative: bool = False
    alt_group: Optional[str] = None
    priority: int = 1
    remark: Optional[str] = None


class BomLineOut(BaseModel):
    id: int
    line_no: int
    material_id: int
    qty_per: Decimal
    unit: str
    scrap_rate: Decimal
    is_alternative: bool
    alt_group: Optional[str]
    priority: int
    remark: Optional[str]

    model_config = {"from_attributes": True}


class BomOut(BaseModel):
    id: int
    product_version_id: int
    status: str
    remark: Optional[str]
    lines: List[BomLineOut] = []

    model_config = {"from_attributes": True}


class BomSaveRequest(BaseModel):
    product_version_id: int
    lines: List[BomLineCreate] = Field(..., min_length=1)
    remark: Optional[str] = None


# ---------- Process Route ----------
class ProcessStepCreate(BaseModel):
    seq: int = 10
    step_code: str
    step_name: str
    step_type: str = "GENERAL"
    work_center: Optional[str] = None
    std_time_sec: Optional[Decimal] = None
    mold_id: Optional[int] = None
    param_json: Optional[str] = None
    remark: Optional[str] = None


class ProcessStepOut(BaseModel):
    id: int
    seq: int
    step_code: str
    step_name: str
    step_type: str
    work_center: Optional[str]
    std_time_sec: Optional[Decimal]
    mold_id: Optional[int]
    param_json: Optional[str]
    remark: Optional[str]

    model_config = {"from_attributes": True}


class RouteOut(BaseModel):
    id: int
    product_version_id: int
    status: str
    remark: Optional[str]
    steps: List[ProcessStepOut] = []

    model_config = {"from_attributes": True}


class RouteSaveRequest(BaseModel):
    product_version_id: int
    steps: List[ProcessStepCreate] = Field(..., min_length=1)
    remark: Optional[str] = None


# ---------- Mold ----------
class MoldCreate(BaseModel):
    code: str
    name: str
    mold_type: str = "DIE"
    life_limit: Optional[int] = None
    product_id: Optional[int] = None
    remark: Optional[str] = None


class MoldOut(BaseModel):
    id: int
    code: str
    name: str
    mold_type: str
    status: str
    life_limit: Optional[int]
    life_used: int
    product_id: Optional[int]
    remark: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Nesting ----------
class NestingCreate(BaseModel):
    product_version_id: int
    layout_code: str
    material_id: int
    sheet_width: Optional[Decimal] = None
    sheet_length: Optional[Decimal] = None
    parts_per_sheet: int = Field(default=1, ge=1)
    utilization_rate: Optional[Decimal] = None
    is_default: bool = False
    remark: Optional[str] = None


class NestingOut(BaseModel):
    id: int
    product_version_id: int
    layout_code: str
    status: str
    material_id: int
    sheet_width: Optional[Decimal]
    sheet_length: Optional[Decimal]
    parts_per_sheet: int
    utilization_rate: Optional[Decimal]
    is_default: bool
    remark: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
