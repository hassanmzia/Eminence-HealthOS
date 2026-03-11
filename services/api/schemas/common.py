"""Common schema utilities — pagination, responses, filters."""

from datetime import datetime
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    offset: int = Field(0, ge=0)
    limit: int = Field(20, ge=1, le=100)


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    offset: int
    limit: int


class MessageResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    detail: str


class HealthOSBase(BaseModel):
    """Base for all HealthOS schemas with shared config."""
    model_config = ConfigDict(from_attributes=True)
