# -*- coding: utf-8-sig -*-
r"""Table data models for FormatForge.

مدل‌های داده جدول برای FormatForge.
Pydantic models representing parsed table structures.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class CellStyle(BaseModel):
    r"""Style information for a table cell.

    اطلاعات استایل برای یک سلول جدول.
    """

    background_color: Optional[str] = None
    text_align: Optional[str] = None
    css_class: Optional[str] = None
    border_top: Optional[str] = None
    border_bottom: Optional[str] = None


class TableCell(BaseModel):
    r"""Represents a single cell in a table.

    نمایانگر یک سلول در جدول.
    """

    content: str = ""
    rowspan: int = 1
    colspan: int = 1
    style: Optional[CellStyle] = None
    is_header: bool = False


class TableModel(BaseModel):
    r"""Complete table model after parsing.

    مدل کامل جدول پس از تحلیل.
    Attributes:
        headers: لیست ردیف‌های سرستون
        rows: لیست ردیف‌های بدنه
        caption: عنوان جدول
        label: برچسب ارجاع
        is_rtl: جهت راست‌به‌چپ
        is_long: جدول طولانی (longtable)
        is_landscape: جدول افقی (sidewaystable)
        is_full_width: عرض کامل (tabularx)
        has_colors: دارای رنگ‌بندی
        has_merged_cells: دارای سلول‌های ادغامی
        col_alignments: ترازبندی ستون‌ها
        caption_position: محل عنوان (above/below)
    """

    headers: List[List[TableCell]] = Field(default_factory=list)
    rows: List[List[TableCell]] = Field(default_factory=list)
    caption: Optional[str] = None
    label: Optional[str] = None
    is_rtl: bool = True
    is_long: bool = False
    is_landscape: bool = False
    is_full_width: bool = False
    has_colors: bool = False
    has_merged_cells: bool = False
    col_alignments: List[str] = Field(default_factory=list)
    caption_position: str = "below"

    @property
    def is_simple(self) -> bool:
        r"""Check if table can be rendered as simple Markdown pipe table.

        بررسی اینکه آیا جدول به صورت Markdown ساده قابل نمایش است.
        """
        return (
            not self.has_colors
            and not self.has_merged_cells
            and not self.is_landscape
            and not self.is_long
            and len(self.headers) <= 1
        )

    @property
    def col_count(self) -> int:
        r"""Number of columns in the table.

        تعداد ستون‌های جدول.
        """
        if self.headers:
            return len(self.headers[0])
        if self.rows:
            return len(self.rows[0])
        return 0
