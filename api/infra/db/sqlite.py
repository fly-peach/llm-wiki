"""SQLite 连接池 + Repository 基类

提供异步 SQLite 连接管理、序列化写锁、以及泛型 Repository 抽象。
"""

from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path
from typing import Any

import aiosqlite

# 全局写锁：SQLite 不支持并发写，所有写操作必须串行化
_write_lock = asyncio.Lock()


def serialized_write():
    """获取写锁的上下文管理器，确保同一时间只有一个写操作。"""
    return _write_lock


async def create_pool(db_path: str | Path) -> aiosqlite.Connection:
    """创建 SQLite 连接，启用 WAL 模式、外键约束和超时设置。

    参数:
        db_path: .db 文件的路径

    返回:
        已配置的 aiosqlite 连接
    """
    db_path = Path(db_path)
    db = await aiosqlite.connect(str(db_path))
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.execute("PRAGMA busy_timeout=5000")

    # 轻量迁移：补齐老版本 DB 可能缺失的列（仅当表已存在时；新库尚未建表，跳过）
    cur = await db.execute("PRAGMA table_info(workspace)")
    cols = {row[1] for row in await cur.fetchall()}
    if cols and "kind" not in cols:
        await db.execute("ALTER TABLE workspace ADD COLUMN kind TEXT NOT NULL DEFAULT 'wiki'")

    return db


async def execute_schema(db: aiosqlite.Connection, schema_path: str | Path) -> None:
    """执行 SQL schema 文件（幂等，使用 IF NOT EXISTS）。

    参数:
        db: 已连接的数据库
        schema_path: .sql 文件的路径
    """
    schema_sql = Path(schema_path).read_text(encoding="utf-8")
    await db.executescript(schema_sql)
    await db.commit()


def row_to_dict(cursor: aiosqlite.Cursor, row: sqlite3.Row | None) -> dict[str, Any] | None:
    """将 sqlite3.Row 转为 dict。"""
    if row is None:
        return None
    return dict(zip([col[0] for col in cursor.description], row))


class BaseRepository:
    """Repository 基类，提供通用 CRUD 辅助方法。"""

    def __init__(self, db: aiosqlite.Connection):
        self._db = db

    @property
    def db(self) -> aiosqlite.Connection:
        return self._db

    async def _fetchone(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        cursor = await self._db.execute(sql, params)
        row = await cursor.fetchone()
        return row_to_dict(cursor, row)

    async def _fetchall(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        cursor = await self._db.execute(sql, params)
        rows = await cursor.fetchall()
        result: list[dict[str, Any]] = []
        for r in rows:
            d = row_to_dict(cursor, r)
            if d is not None:
                result.append(d)
        return result

    async def _execute(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        return await self._db.execute(sql, params)


class SQLiteDocumentRepository(BaseRepository):
    """文档仓库 — 封装 documents 表的全部 CRUD 操作。"""

    # ── 查询 ─────────────────────────────────────────────

    async def get(self, doc_id: str) -> dict[str, Any] | None:
        return await self._fetchone(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        )

    async def get_by_path(self, relative_path: str) -> dict[str, Any] | None:
        return await self._fetchone(
            "SELECT * FROM documents WHERE relative_path = ?", (relative_path,)
        )

    async def list_all(
        self,
        source_kind: str | None = None,
        path: str | None = None,
        status: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM documents WHERE 1=1"
        params: list[Any] = []

        if source_kind:
            sql += " AND source_kind = ?"
            params.append(source_kind)
        if path:
            sql += " AND path LIKE ?"
            params.append(f"{path}%")
        if status:
            sql += " AND status = ?"
            params.append(status)
        if entity_type:
            sql += " AND entity_type = ?"
            params.append(entity_type)

        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        return await self._fetchall(sql, tuple(params))

    async def count(
        self,
        source_kind: str | None = None,
        status: str | None = None,
        entity_type: str | None = None,
    ) -> int:
        sql = "SELECT COUNT(*) as cnt FROM documents WHERE 1=1"
        params: list[Any] = []
        if source_kind:
            sql += " AND source_kind = ?"
            params.append(source_kind)
        if status:
            sql += " AND status = ?"
            params.append(status)
        if entity_type:
            sql += " AND entity_type = ?"
            params.append(entity_type)
        row = await self._fetchone(sql, tuple(params))
        return row["cnt"] if row else 0

    # ── 写入 ─────────────────────────────────────────────

    async def insert(self, **fields) -> str:
        """插入文档，返回生成的 id。"""
        columns = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        values = tuple(fields.values())

        async with serialized_write():
            await self._db.execute(
                f"INSERT INTO documents ({columns}) VALUES ({placeholders})",
                values,
            )
            await self._db.commit()

        # 查询刚插入的 id
        row = await self._fetchone(
            "SELECT id FROM documents WHERE relative_path = ?",
            (fields.get("relative_path"),),
        )
        return row["id"] if row else ""

    async def update(self, doc_id: str, version: int, **fields) -> bool:
        """乐观锁更新，返回是否成功。"""
        if not fields:
            return True

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values())
        values.extend([doc_id, version])

        async with serialized_write():
            cursor = await self._db.execute(
                f"UPDATE documents SET {set_clause}, version = version + 1, "
                f"updated_at = datetime('now') "
                f"WHERE id = ? AND version = ?",
                tuple(values),
            )
            await self._db.commit()
            return cursor.rowcount > 0

    async def delete(self, doc_id: str) -> bool:
        async with serialized_write():
            cursor = await self._db.execute(
                "DELETE FROM documents WHERE id = ?", (doc_id,)
            )
            await self._db.commit()
            return cursor.rowcount > 0

    # ── FTS5 搜索 ────────────────────────────────────────

    async def search(
        self, query: str, limit: int = 20, annotated_only: bool = False,
    ) -> list[dict[str, Any]]:
        """全文搜索（FTS5），返回匹配的文档块及关联文档信息。"""
        extra = "AND c.has_highlight = 1" if annotated_only else ""
        return await self._fetchall(
            f"""
            SELECT d.*, c.content as chunk_content, c.chunk_index,
                   c.header_breadcrumb, c.token_count
            FROM chunks_fts f
            JOIN document_chunks c ON f.rowid = c.rowid
            JOIN documents d ON c.document_id = d.id
            WHERE chunks_fts MATCH ? {extra}
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        )


class SQLiteChunkRepository(BaseRepository):
    """块仓库 — 管理 document_chunks 表，支撑高亮→chunk 联动。"""

    async def get_chunks_for_doc(self, doc_id: str) -> list[dict[str, Any]]:
        """获取文档的全部块（精简字段，用于高亮映射）。"""
        return await self._fetchall(
            "SELECT id, chunk_index, source_content, page, start_char "
            "FROM document_chunks WHERE document_id = ? "
            "ORDER BY chunk_index",
            (doc_id,),
        )

    async def update_chunk_content(
        self,
        chunk_id: str,
        content: str,
        annotations_text: str | None,
        has_highlight: int,
    ) -> None:
        """更新块的物化内容及高亮标记。"""
        await self._db.execute(
            "UPDATE document_chunks "
            "SET content = ?, annotations_text = ?, has_highlight = ? "
            "WHERE id = ?",
            (content, annotations_text, has_highlight, chunk_id),
        )
