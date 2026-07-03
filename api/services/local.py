"""本地模式服务实现

基于 SQLite 的单用户本地实现。所有数据存储在本地磁盘的 .llmwiki/index.db 中。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite

from infra.db.sqlite import (
    BaseRepository,
    SQLiteDocumentRepository,
    SQLiteChunkRepository,
    create_pool,
    serialized_write,
)
from infra.workspace.init import init_workspace as do_init_workspace
from infra.workspace.registry import WorkspaceRegistry
from services.base import WikiService


class LocalWikiService(WikiService):
    """基于 SQLite 的本地 Wiki 服务实现。

    每个工作区拥有独立的 index.db，通过 workspace registry 管理多个工作区。
    """

    def __init__(self, registry_path: str | Path):
        self._registry_path = Path(registry_path)
        self._registry = WorkspaceRegistry(registry_path)
        # db 连接缓存: ws_id -> Connection
        self._dbs: dict[str, aiosqlite.Connection] = {}

    async def _get_db(self, ws_id: str) -> aiosqlite.Connection:
        """获取或创建数据库连接（按 ws_id 缓存）。"""
        if ws_id not in self._dbs:
            entry = self._registry.get(ws_id)
            if not entry:
                raise ValueError(f"Workspace not found: {ws_id}")
            db_path = Path(entry["path"]) / ".llmwiki" / "index.db"
            self._dbs[ws_id] = await create_pool(db_path)
        return self._dbs[ws_id]

    def _repo(self, db: aiosqlite.Connection) -> SQLiteDocumentRepository:
        return SQLiteDocumentRepository(db)

    # ── 工作区 ──────────────────────────────────────────

    async def init_workspace(self, path: Path) -> str:
        ws_id = await do_init_workspace(path)
        from infra.workspace.init import _now_iso

        self._registry.register({
            "id": ws_id,
            "name": path.name,
            "path": str(path.resolve()),
            "created_at": _now_iso(),
        })
        return ws_id

    async def get_workspace(self, ws_id: str) -> dict[str, Any] | None:
        db = await self._get_db(ws_id)
        cursor = await db.execute("SELECT * FROM workspace WHERE id = ?", (ws_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(zip([col[0] for col in cursor.description], row))

    # ── 文档查询 ────────────────────────────────────────

    async def get_document(self, doc_id: str) -> dict[str, Any] | None:
        # 遍历所有已缓存的工作区查找
        for ws_id in self._dbs:
            repo = self._repo(self._dbs[ws_id])
            doc = await repo.get(doc_id)
            if doc:
                return doc
        return None

    async def get_document_by_path(
        self, ws_id: str, relative_path: str
    ) -> dict[str, Any] | None:
        db = await self._get_db(ws_id)
        return await self._repo(db).get_by_path(relative_path)

    async def list_documents(
        self,
        ws_id: str,
        source_kind: str | None = None,
        path: str | None = None,
        status: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        db = await self._get_db(ws_id)
        return await self._repo(db).list_all(
            source_kind=source_kind, path=path, status=status,
            entity_type=entity_type, limit=limit, offset=offset,
        )

    async def count_documents(
        self,
        ws_id: str,
        source_kind: str | None = None,
        status: str | None = None,
        entity_type: str | None = None,
    ) -> int:
        db = await self._get_db(ws_id)
        return await self._repo(db).count(
            source_kind=source_kind, status=status, entity_type=entity_type,
        )

    # ── 文档写入 ────────────────────────────────────────

    async def create_document(self, ws_id: str, **fields) -> str:
        db = await self._get_db(ws_id)
        return await self._repo(db).insert(**fields)

    async def update_document(self, doc_id: str, version: int, **fields) -> bool:
        # 遍历查找所属工作区
        for ws_id in list(self._dbs.keys()):
            db = self._dbs[ws_id]
            repo = self._repo(db)
            doc = await repo.get(doc_id)
            if doc:
                return await repo.update(doc_id, version, **fields)
        return False

    async def delete_document(self, doc_id: str) -> bool:
        for ws_id in list(self._dbs.keys()):
            db = self._dbs[ws_id]
            repo = self._repo(db)
            doc = await repo.get(doc_id)
            if doc:
                return await repo.delete(doc_id)
        return False

    # ── 搜索 ────────────────────────────────────────────

    async def search(
        self, ws_id: str, query: str, limit: int = 20,
        annotated_only: bool = False,
    ) -> list[dict[str, Any]]:
        db = await self._get_db(ws_id)
        return await self._repo(db).search(query, limit, annotated_only=annotated_only)

    # ── 清理 ────────────────────────────────────────────

    async def close(self) -> None:
        """关闭所有数据库连接。"""
        for db in self._dbs.values():
            await db.close()
        self._dbs.clear()

    # ── 高亮 → Chunk 同步 ────────────────────────────

    async def sync_highlight_chunks(
        self,
        doc_id: str,
        old_highlights: list[dict],
        new_highlights: list[dict],
    ) -> None:
        """高亮变更后将 annotations 物化到关联的 document_chunks。

        在 documents.highlights JSON 写入的同一事务中调用，
        确保 FTS5 索引与高亮数据一致。
        """
        from services.highlight_chunks import (
            ChunkRecord,
            all_affected_chunks,
            iter_chunks_with_annotations,
        )

        # 找到文档所属工作区
        db = None
        for ws_id in self._dbs:
            repo = self._repo(self._dbs[ws_id])
            doc = await repo.get(doc_id)
            if doc:
                db = self._dbs[ws_id]
                break
        if db is None:
            return

        chunk_repo = SQLiteChunkRepository(db)
        chunk_rows = await chunk_repo.get_chunks_for_doc(doc_id)
        chunks = [
            ChunkRecord(
                id=r["id"],
                chunk_index=r["chunk_index"],
                source_content=r["source_content"] or r.get("content", ""),
                page=r.get("page"),
                start_char=r.get("start_char"),
            )
            for r in chunk_rows
        ]

        affected = all_affected_chunks(chunks, old_highlights, new_highlights)
        if not affected:
            return

        async with serialized_write():
            try:
                for chunk, ann_text, has_hl, new_content in iter_chunks_with_annotations(
                    chunks, affected, new_highlights,
                ):
                    await chunk_repo.update_chunk_content(
                        chunk.id, new_content, ann_text, 1 if has_hl else 0,
                    )
                await db.commit()
            except Exception:
                await db.rollback()
                raise
