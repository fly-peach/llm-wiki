"""HTML 解析器数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Image:
    """HTML 图片信息"""
    src: str
    alt: str = ""
    title: str = ""
    width: int | None = None
    height: int | None = None


@dataclass
class FormField:
    """表单字段"""
    label: str
    name: str
    field_type: str  # text, select, radio, checkbox, textarea
    required: bool = False
    placeholder: str = ""
    options: list[str] = field(default_factory=list)


@dataclass
class Form:
    """HTML 表单"""
    id: str = ""
    name: str = ""
    action: str = ""
    method: str = "GET"
    fields: list[FormField] = field(default_factory=list)


@dataclass
class ParseResult:
    """HTML 解析结果"""
    title: str = ""
    content: str = ""          # Markdown 正文
    images: list[Image] = field(default_factory=list)
    forms: list[dict] = field(default_factory=list)
    highlights: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)  # {url, date, author, ...}
