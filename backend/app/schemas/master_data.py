"""基础数据 Pydantic Schema"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------- Unit ----------
class UnitCreate(BaseModel):
    code: str = Field(..., max_length=16)
    name: str = Field(..., max_length=64)


class UnitOut(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Material ----------
class MaterialCreate(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    spec: Optional[str] = None
    material_type: str = "RAW"
    base_unit: str = "PCS"
    is_batch_managed: bool = False
    is_roll_managed: bool = False
    remark: Optional[str] = None


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    spec: Optional[str] = None
    material_type: Optional[str] = None
    base_unit: Optional[str] = None
    is_batch_managed: Optional[bool] = None
    is_roll_managed: Optional[bool] = None
    is_active: Optional[bool] = None
    remark: Optional[str] = None


class MaterialOut(BaseModel):
    id: int
    code: str
    name: str
    spec: Optional[str]
    material_type: str
    base_unit: str
    is_batch_managed: bool
    is_roll_managed: bool
    is_active: bool
    remark: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Supplier ----------
class SupplierCreate(BaseModel):
    code: str = Field(..., max_length=64)
    name: str = Field(..., max_length=128)
    short_name: Optional[str] = None
    contact: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    remark: Optional[str] = None


class SupplierOut(BaseModel):
    id: int
    code: str
    name: str
    short_name: Optional[str]
    contact: Optional[str]
    phone: Optional[str]
    address: Optional[str]
    is_active: bool
    remark: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Warehouse ----------
class WarehouseCreate(BaseModel):
    code: str = Field(..., max_length=32)
    name: str = Field(..., max_length=64)
    warehouse_type: str = "NORMAL"


class WarehouseOut(BaseModel):
    id: int
    code: str
    name: str
    warehouse_type: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- Location ----------
class LocationCreate(BaseModel):
    warehouse_id: int
    code: str = Field(..., max_length=32)
    name: Optional[str] = None


class LocationOut(BaseModel):
    id: int
    warehouse_id: int
    code: str
    name: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
