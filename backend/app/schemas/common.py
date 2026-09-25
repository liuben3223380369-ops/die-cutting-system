"""统一响应与错误模型"""
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """统一成功响应"""
    success: bool = True
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorDetail(BaseModel):
    """错误详情"""
    field: Optional[str] = None
    message: str


class APIErrorResponse(BaseModel):
    """统一错误响应"""
    success: bool = False
    code: int
    message: str
    details: Optional[list[ErrorDetail]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class HealthStatus(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    app_name: str
    version: str
    environment: str
    database: str = "unknown"
