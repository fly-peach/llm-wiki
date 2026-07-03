"""请求/响应 Pydantic 模型"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ── 文档 ──────────────────────────────────────────────

class DocumentUpdateRequest(BaseModel):
    title: str | None = None
    path: str | None = None
    tags: str | None = None  # JSON list
    status: str | None = None
    entity_type: str | None = None
    domain: str | None = None
    metadata: str | None = None  # JSON


class DocumentContentUpdate(BaseModel):
    content: str
    expected_version: int = Field(default=0, ge=0)


class HighlightUpsert(BaseModel):
    highlight_id: str
    data: dict[str, Any]


class HighlightsReplace(BaseModel):
    highlights: list[dict[str, Any]]
    expected_version: int | None = None


class CreateNoteRequest(BaseModel):
    filename: str
    path: str = "/wiki/"
    content: str = ""
    title: str | None = None


# ── 知识库 ────────────────────────────────────────────

class KnowledgeBaseCreate(BaseModel):
    name: str
    description: str = ""
    kind: str = "wiki"


# ── 批量删除 ──────────────────────────────────────────

class BulkDeleteRequest(BaseModel):
    doc_ids: list[str]
