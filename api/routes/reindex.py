"""重建索引 API

- POST /v1/reindex  扫描工作区全部文件并重建索引

用于首次初始化后的全量索引，或修复索引不一致。
支持 chunk_size 参数自定义分块大小。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query

from deps import find_valid_workspace, get_service
from domain.file_types import SIMPLE_TEXT, EXTRACTION, infer_source_kind
from domain.watcher import _index_file, _save_chunks_for_doc, _should_ignore
from services.local import LocalWikiService
from services.chunker import ChunkConfig

router = APIRouter(prefix="/v1", tags=["reindex"])


@router.post("/reindex")
async def reindex_workspace(
    ws_id: str = "",
    chunk_size: int = Query(default=512, ge=64, le=4096, description="分块大小（token 数）"),
    svc: LocalWikiService = Depends(get_service),
):
    """扫描工作区文件系统，重建全部索引。

    - chunk_size: 分块 token 大小，默认 512，范围 64~4096
    - 若文档已有 chunk 则跳过（内容未变时）；若缺失则补写
    """
    if not ws_id:
        ws_id = find_valid_workspace(svc)
        if not ws_id:
            raise HTTPException(
                status_code=400,
                detail="No workspace registered. Create one first: POST /v1/workspaces",
            )

    entry = svc._registry.get(ws_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace = Path(entry["path"])
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="Workspace directory not found")

    indexed = 0
    skipped = 0
    errors = 0

    # 遍历工作区根目录和 wiki/ 目录
    for scan_dir in ["", "wiki"]:
        target = workspace / scan_dir if scan_dir else workspace
        if not target.exists():
            continue

        for fp in target.rglob("*"):
            if not fp.is_file():
                continue
            if _should_ignore(str(fp)):
                skipped += 1
                continue

            try:
                doc_id = await _index_file(svc, ws_id, workspace, str(fp))
                if doc_id:
                    indexed += 1
                else:
                    skipped += 1
            except Exception:
                errors += 1

    # 补写缺失的 chunk（使用自定义 chunk_size）
    chunked_count = await _backfill_missing_chunks(svc, ws_id, chunk_size)

    return {
        "status": "ok",
        "workspace_id": ws_id,
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
        "chunk_size": chunk_size,
        "chunks_backfilled": chunked_count,
    }


async def _backfill_missing_chunks(
    svc: LocalWikiService,
    ws_id: str,
    chunk_size: int,
) -> int:
    """遍历所有文档，为缺失 chunk 的文档按指定大小补写分块。"""
    from domain.watcher import _has_chunks, _save_chunks_for_doc
    from services.chunker import ChunkConfig

    # 覆写 watcher 模块的全局默认 chunk_size——简单方案
    # 真正的生产方案应通过 watcher._save_chunks_for_doc 接受 config 参数
    doc_count = await svc.count_documents(ws_id)
    if doc_count == 0:
        return 0

    docs = await svc.list_documents(ws_id, limit=doc_count + 100)
    backfilled = 0

    for doc in docs:
        doc_id = doc["id"]
        if await _has_chunks(svc, ws_id, doc_id):
            continue
        content = doc.get("content", "")
        if not content or not content.strip():
            continue

        config = ChunkConfig.from_size(chunk_size)
        chunks = chunk_text(content, config=config)
        if not chunks:
            continue

        db = await svc._get_db(ws_id)
        from infra.db.sqlite import serialized_write
        async with serialized_write():
            await db.execute(
                "DELETE FROM document_chunks WHERE document_id = ?",
                (doc_id,),
            )
            for ch in chunks:
                await db.execute(
                    """INSERT INTO document_chunks
                       (document_id, chunk_index, content, source_content,
                        page, start_char, token_count, header_breadcrumb)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        doc_id, ch.index, ch.content, ch.content,
                        ch.page, ch.start_char, ch.token_count, ch.header_breadcrumb,
                    ),
                )
            await db.commit()
        backfilled += 1

    return backfilled
