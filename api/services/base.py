"""服务抽象接口（ABC）

定义 LLM Wiki 的核心服务契约。本地实现见 local.py，未来可扩展云端实现。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class WikiService(ABC):
    """Wiki 核心服务抽象 — 文档管理 + 工作区操作。"""

    # ── 工作区 ──────────────────────────────────────────

    @abstractmethod
    async def init_workspace(self, path: Path) -> str:
        """初始化工作区，返回 ws_id。"""
        ...

    @abstractmethod
    async def get_workspace(self, ws_id: str) -> dict[str, Any] | None:
        """获取工作区信息。"""
        ...

    # ── 文档查询 ────────────────────────────────────────

    @abstractmethod
    async def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """获取单个文档。"""
        ...

    @abstractmethod
    async def get_document_by_path(
        self, ws_id: str, relative_path: str
    ) -> dict[str, Any] | None:
        """按相对路径获取文档。"""
        ...

    @abstractmethod
    async def list_documents(
        self,
        ws_id: str,
        source_kind: str | None = None,
        path: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """列出文档。"""
        ...

    @abstractmethod
    async def count_documents(
        self,
        ws_id: str,
        source_kind: str | None = None,
        status: str | None = None,
    ) -> int:
        """统计文档数量。"""
        ...

    # ── 文档写入 ────────────────────────────────────────

    @abstractmethod
    async def create_document(self, ws_id: str, **fields) -> str:
        """创建文档，返回 doc_id。"""
        ...

    @abstractmethod
    async def update_document(
        self, doc_id: str, version: int, **fields
    ) -> bool:
        """乐观锁更新文档。"""
        ...

    @abstractmethod
    async def delete_document(self, doc_id: str) -> bool:
        """删除文档及其关联数据（级联）。"""
        ...

    # ── 搜索 ────────────────────────────────────────────

    @abstractmethod
    async def search(
        self, ws_id: str, query: str, limit: int = 20,
        annotated_only: bool = False,
    ) -> list[dict[str, Any]]:
        """全文搜索，可选仅搜索含高亮标注的块。"""
        ...
