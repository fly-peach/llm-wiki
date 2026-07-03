"""文件系统监控 + 自动索引

使用 watchfiles 监控工作区文件变化，自动将文件元数据写入 documents 表。
包含防回环机制：应用自身写入文件时跳过监控事件。
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from watchfiles import Change, awatch

from domain.file_types import (
    EXTRACTION,
    infer_source_kind,
    is_simple_text,
)

if TYPE_CHECKING:
    from services.local import LocalWikiService

# ── 防回环机制 ────────────────────────────────────────
# 字典只增不减，简单可靠（总文件数有限）
_recently_written: dict[str, float] = {}
COOLDOWN_SECONDS = 3.0  # 冷却期（秒）


def mark_written(path: str) -> None:
    """标记文件由应用写入，watcher 在冷却期内跳过。"""
    resolved = str(Path(path).resolve())
    _recently_written[resolved] = time.monotonic()


def _is_recently_written(path: str) -> bool:
    """检查文件是否在冷却期内被应用写入。"""
    resolved = str(Path(path).resolve())
    ts = _recently_written.get(resolved)
    if ts is None:
        return False
    if time.monotonic() - ts > COOLDOWN_SECONDS:
        del _recently_written[resolved]
        return False
    return True


# ── 忽略目录 ──────────────────────────────────────────
_IGNORE_DIRS = frozenset({
    ".llmwiki", ".git", "node_modules", "__pycache__",
    ".venv", "venv", ".idea", ".vscode", ".conda",
})

_IGNORE_PREFIXES = (".", "~")  # 忽略隐藏文件和临时文件


def _should_ignore(path_str: str) -> bool:
    """判断文件/目录是否应被忽略。"""
    parts = set(Path(path_str).parts)
    if parts & _IGNORE_DIRS:
        return True
    name = Path(path_str).name
    if name.startswith(_IGNORE_PREFIXES):
        return True
    # 忽略 .db 文件（数据库自身）
    if name.endswith(".db") or name.endswith(".db-journal") or name.endswith(".db-wal"):
        return True
    return False


# ── 索引核心 ──────────────────────────────────────────

async def _index_file(
    svc: "LocalWikiService",
    ws_id: str,
    workspace: Path,
    file_path: str,
) -> str | None:
    """索引单个文件，返回 doc_id 或 None（跳过时）。

    流程：
      1. 计算 relative_path
      2. 推断 source_kind
      3. 读取元数据（file_size, mtime_ns）
      4. 纯文本 → 读取内容，status='ready'
         需提取 → status='pending'
      5. 计算 content_hash
      6. 按 relative_path 查重 → INSERT 或 UPDATE
    """
    try:
        fp = Path(file_path)
        if not fp.is_file():
            return None
        if _should_ignore(str(fp)):
            return None

        # 路径
        relative_path = str(fp.relative_to(workspace)).replace("\\", "/")
        filename = fp.name
        extension = fp.suffix.lstrip(".").lower()

        # source_kind
        source_kind = infer_source_kind(relative_path)

        # 文件元数据
        stat = fp.stat()
        file_size = stat.st_size
        mtime_ns = stat.st_mtime_ns

        # 内容 + 状态
        content: str | None = None
        if is_simple_text(extension):
            try:
                content = fp.read_text(encoding="utf-8")
                status = "ready"
            except (UnicodeDecodeError, OSError):
                # 二进制但扩展名像文本 → 标记 pending
                content = None
                status = "pending"
        elif extension in EXTRACTION:
            status = "pending"
        else:
            # 未知类型 → 跳过
            return None

        # content_hash
        content_hash = None
        if content is not None:
            content_hash = hashlib.sha256(content.encode()).hexdigest()

        # 查重
        now = _now_iso()
        existing = await svc.get_document_by_path(ws_id, relative_path)

        if existing:
            # 内容没变 → 只更新 mtime
            if content_hash and existing.get("content_hash") == content_hash:
                await svc.update_document(
                    existing["id"],
                    existing["version"],
                    mtime_ns=mtime_ns,
                    file_size=file_size,
                    last_indexed_at=now,
                    stale_since=None,
                )
                return existing["id"]

            # 内容变了 → 更新
            update_fields: dict = {
                "mtime_ns": mtime_ns,
                "file_size": file_size,
                "last_indexed_at": now,
                "status": status,
                "stale_since": None,
            }
            if content is not None:
                update_fields["content"] = content
                update_fields["content_hash"] = content_hash
            await svc.update_document(
                existing["id"], existing["version"], **update_fields
            )
            return existing["id"]

        else:
            # 新文件 → 插入
            fields: dict = {
                "user_id": "local-user",
                "filename": filename,
                "title": filename,
                "path": f"/{source_kind}/",
                "relative_path": relative_path,
                "source_kind": source_kind,
                "file_type": extension,
                "file_size": file_size,
                "status": status,
                "mtime_ns": mtime_ns,
                "last_indexed_at": now,
            }
            if content is not None:
                fields["content"] = content
                fields["content_hash"] = content_hash
            return await svc.create_document(ws_id, **fields)

    except Exception:
        # 索引失败不应阻断监控循环
        import traceback
        traceback.print_exc()
        return None


async def _remove_file(
    svc: "LocalWikiService",
    ws_id: str,
    workspace: Path,
    file_path: str,
) -> bool:
    """从索引中移除已删除的文件。"""
    try:
        fp = Path(file_path)
        relative_path = str(fp.relative_to(workspace)).replace("\\", "/")
        doc = await svc.get_document_by_path(ws_id, relative_path)
        if doc:
            return await svc.delete_document(doc["id"])
    except Exception:
        import traceback
        traceback.print_exc()
    return False


# ── 监控循环 ──────────────────────────────────────────

async def watch_workspace(
    svc: "LocalWikiService",
    ws_id: str,
    workspace: Path,
    stop_event: asyncio.Event | None = None,
) -> None:
    """启动文件系统监控循环（后台任务）。

    参数:
        svc: LocalWikiService 实例
        ws_id: 工作区 ID
        workspace: 工作区根目录
        stop_event: 外部停止信号（可选）
    """
    if stop_event is None:
        stop_event = asyncio.Event()

    print(f"[watcher] Starting watch on: {workspace}")

    async for changes in awatch(str(workspace)):
        if stop_event.is_set():
            print("[watcher] Stopped")
            return

        for change_type, raw_path in changes:
            path_str = str(raw_path)

            if _should_ignore(path_str):
                continue
            if _is_recently_written(path_str):
                continue

            try:
                if change_type in (Change.added, Change.modified):
                    doc_id = await _index_file(svc, ws_id, workspace, path_str)
                    if doc_id:
                        print(f"[watcher] indexed: {Path(path_str).name} → {doc_id[:8]}...")

                elif change_type == Change.deleted:
                    removed = await _remove_file(svc, ws_id, workspace, path_str)
                    if removed:
                        print(f"[watcher] removed: {Path(path_str).name}")
            except Exception:
                import traceback
                traceback.print_exc()


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
