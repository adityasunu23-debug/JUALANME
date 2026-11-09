"""Shared response envelopes."""
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str
    success: bool = True


class PageMeta(BaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


class Page(BaseModel, Generic[T]):
    items: List[T] = Field(default_factory=list)
    meta: PageMeta = Field(default_factory=PageMeta)

    @classmethod
    def build(cls, items: List[T], total: int, page: int, page_size: int) -> "Page[T]":
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        return cls(
            items=items,
            meta=PageMeta(
                total=total, page=page, page_size=page_size, total_pages=total_pages
            ),
        )


class StatusUpdate(BaseModel):
    status: str


class BulkDeleteRequest(BaseModel):
    ids: List[int] = Field(default_factory=list)


class AmountStat(BaseModel):
    label: Optional[str] = None
    value: float = 0
    count: int = 0