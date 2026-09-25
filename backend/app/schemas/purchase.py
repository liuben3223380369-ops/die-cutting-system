"""采购模块 Schema"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------- 采购申请 ----------
class PRLineCreate(BaseModel):
    material_id: int
    qty: Decimal = Field(..., gt=0)
    unit: str = "PCS"
    required_date: Optional[date] = None
    remark: Optional[str] = None


class PurchaseRequestCreate(BaseModel):
    request_date: date
    requester: Optional[str] = None
    remark: Optional[str] = None
    lines: List[PRLineCreate] = Field(..., min_length=1)


class PRLineOut(BaseModel):
    id: int
    line_no: int
    material_id: int
    qty: Decimal
    unit: str
    required_date: Optional[date]
    remark: Optional[str]

    model_config = {"from_attributes": True}


class PurchaseRequestOut(BaseModel):
    id: int
    doc_no: str
    status: str
    request_date: date
    requester: Optional[str]
    remark: Optional[str]
    created_at: datetime
    lines: List[PRLineOut] = []

    model_config = {"from_attributes": True}


# ---------- 采购订单 ----------
class POLineCreate(BaseModel):
    material_id: int
    qty: Decimal = Field(..., gt=0)
    unit: str = "PCS"
    unit_price: Optional[Decimal] = None
    expected_date: Optional[date] = None
    remark: Optional[str] = None


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    order_date: date
    expected_date: Optional[date] = None
    currency: str = "CNY"
    remark: Optional[str] = None
    request_id: Optional[int] = None
    lines: List[POLineCreate] = Field(..., min_length=1)


class POLineOut(BaseModel):
    id: int
    line_no: int
    material_id: int
    qty: Decimal
    qty_received: Decimal
    unit: str
    unit_price: Optional[Decimal]
    expected_date: Optional[date]
    remark: Optional[str]

    model_config = {"from_attributes": True}


class PurchaseOrderOut(BaseModel):
    id: int
    doc_no: str
    status: str
    supplier_id: int
    order_date: date
    expected_date: Optional[date]
    currency: str
    remark: Optional[str]
    request_id: Optional[int]
    created_at: datetime
    lines: List[POLineOut] = []

    model_config = {"from_attributes": True}


# ---------- 到货 ----------
class ArrivalLineCreate(BaseModel):
    order_line_id: int
    material_id: int
    qty: Decimal = Field(..., gt=0)
    unit: str = "PCS"
    batch_no: str = ""
    roll_no: str = ""
    remark: Optional[str] = None


class ArrivalNoteCreate(BaseModel):
    order_id: int
    arrival_date: date
    warehouse_id: int  # 暂收/待检仓
    remark: Optional[str] = None
    lines: List[ArrivalLineCreate] = Field(..., min_length=1)


class ArrivalLineOut(BaseModel):
    id: int
    line_no: int
    order_line_id: int
    material_id: int
    qty: Decimal
    unit: str
    batch_no: str
    roll_no: str
    qc_status: str
    qty_passed: Decimal
    qty_failed: Decimal
    remark: Optional[str]

    model_config = {"from_attributes": True}


class ArrivalNoteOut(BaseModel):
    id: int
    doc_no: str
    status: str
    order_id: int
    supplier_id: int
    arrival_date: date
    warehouse_id: int
    remark: Optional[str]
    created_at: datetime
    lines: List[ArrivalLineOut] = []

    model_config = {"from_attributes": True}


# ---------- IQC ----------
class IQCCreate(BaseModel):
    arrival_line_id: int
    result: str = Field(..., pattern="^(PASSED|FAILED|PARTIAL)$")
    qty_inspected: Decimal = Field(..., gt=0)
    qty_passed: Decimal = Field(..., ge=0)
    qty_failed: Decimal = Field(..., ge=0)
    inspector: Optional[str] = None
    inspect_date: date
    defect_codes: Optional[str] = None
    remark: Optional[str] = None
    # 合格入库目标仓（合格部分入库）
    target_warehouse_id: Optional[int] = None
    # 不合格隔离仓（可选）
    hold_warehouse_id: Optional[int] = None


class IQCOut(BaseModel):
    id: int
    doc_no: str
    arrival_line_id: int
    material_id: int
    result: str
    qty_inspected: Decimal
    qty_passed: Decimal
    qty_failed: Decimal
    inspector: Optional[str]
    inspect_date: date
    defect_codes: Optional[str]
    remark: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------- 采购退货 ----------
class ReturnLineCreate(BaseModel):
    material_id: int
    qty: Decimal = Field(..., gt=0)
    unit: str = "PCS"
    batch_no: str = ""
    roll_no: str = ""
    order_line_id: Optional[int] = None
    remark: Optional[str] = None


class PurchaseReturnCreate(BaseModel):
    supplier_id: int
    return_date: date
    warehouse_id: int
    order_id: Optional[int] = None
    reason_code: Optional[str] = None
    remark: Optional[str] = None
    lines: List[ReturnLineCreate] = Field(..., min_length=1)


class ReturnLineOut(BaseModel):
    id: int
    line_no: int
    material_id: int
    qty: Decimal
    unit: str
    batch_no: str
    roll_no: str
    order_line_id: Optional[int]
    remark: Optional[str]

    model_config = {"from_attributes": True}


class PurchaseReturnOut(BaseModel):
    id: int
    doc_no: str
    status: str
    supplier_id: int
    order_id: Optional[int]
    return_date: date
    warehouse_id: int
    reason_code: Optional[str]
    remark: Optional[str]
    created_at: datetime
    lines: List[ReturnLineOut] = []

    model_config = {"from_attributes": True}


class PriceHistoryOut(BaseModel):
    id: int
    supplier_id: int
    material_id: int
    unit_price: Decimal
    currency: str
    effective_date: date
    source_type: str
    source_id: str
    remark: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
