"""库存 Schema"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class StockInRequest(BaseModel):
    source_type: str = Field(..., description="来源类型，如 PURCHASE_IN")
    source_id: str = Field(..., description="来源单据号")
    material_id: int
    warehouse_id: int
    qty: Decimal = Field(..., gt=0)
    location_id: Optional[int] = None
    batch_no: str = ""
    roll_no: str = ""
    unit: str = "PCS"
    source_line_id: Optional[str] = None
    reason_code: Optional[str] = None
    remark: Optional[str] = None


class StockOutRequest(BaseModel):
    source_type: str
    source_id: str
    material_id: int
    warehouse_id: int
    qty: Decimal = Field(..., gt=0)
    location_id: Optional[int] = None
    batch_no: str = ""
    roll_no: str = ""
    unit: str = "PCS"
    source_line_id: Optional[str] = None
    reason_code: Optional[str] = None
    remark: Optional[str] = None
    allow_negative: bool = False


class AdjustRequest(BaseModel):
    material_id: int
    warehouse_id: int
    qty_delta: Decimal = Field(..., description="正数盘盈，负数盘亏")
    source_id: str = Field(default="", description="调整单号，空则自动生成")
    location_id: Optional[int] = None
    batch_no: str = ""
    roll_no: str = ""
    unit: str = "PCS"
    reason_code: Optional[str] = None
    remark: Optional[str] = None


class TransferRequest(BaseModel):

    source_id: str
    material_id: int
    from_warehouse_id: int
    to_warehouse_id: int
    qty: Decimal = Field(..., gt=0)
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    batch_no: str = ""
    roll_no: str = ""
    unit: str = "PCS"
    remark: Optional[str] = None


class StockBalanceOut(BaseModel):
    id: int
    material_id: int
    warehouse_id: int
    location_id: Optional[int]
    batch_no: str
    roll_no: str
    qty: Decimal
    qty_reserved: Decimal
    qty_frozen: Decimal
    available_qty: Decimal  # 计算字段

    model_config = {"from_attributes": True}


class StockLedgerOut(BaseModel):
    id: int
    source_type: str
    source_id: str
    source_line_id: Optional[str]
    material_id: int
    warehouse_id: int
    location_id: Optional[int]
    batch_no: str
    roll_no: str
    qty: Decimal
    unit: str
    direction: str
    original_ledger_id: Optional[int]
    is_reversed: bool
    reason_code: Optional[str]
    remark: Optional[str]
    created_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
