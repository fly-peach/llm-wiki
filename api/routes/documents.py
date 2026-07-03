"""文档 CRUD + 高亮管理 API

- GET    /v1/documents/{id}              文档详情
- GET    /v1/documents/{id}/content       文档内容
- PUT    /v1/documents/{id}/content       更新内容
- PATCH  /v1/documents/{id}              更新元数据
- DELETE /v1/documents/{id}              删除文档
- GET    /v1/documents/{id}/highlights    获取高亮
- PATCH  /v1/documents/{id}/highlights    批量替换高亮
- POST   /v1/documents/{id}/highlights    单个高亮 upsert
- DELETE /v1/documents/{id}/highlights/{hid}  删除高亮
- POST   /v1/documents/bulk-delete        批量删除
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from deps import find_valid_workspace, get_service
from services.local import LocalWikiService
from services.types import (
    BulkDeleteRequest,
    CreateNoteRequest,
    DocumentContentUpdate,
    DocumentUpdateRequest,
    HighlightUpsert,
    HighlightsReplace,
)

router = APIRouter(prefix="/v1/documents", tags=["documents"])


def _get_doc_or_404(svc: LocalWikiService, doc_id: str) -> dict:
    """获取文档，不存在则 404。"""
    doc = svc.get_document_sync(doc_id)  # type: ignore[attr-defined]
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


# ── 文档详情 ──────────────────────────────────────────

@router.get("/{doc_id}", operation_id="get_document", summary="获取单个文档的元数据(文件名、类型、状态等)")
async def get_document(
    doc_id: str,
    svc: LocalWikiService = Depends(get_service),
):
    """获取单个文档元数据。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{doc_id}/content", operation_id="read_document", summary="读取文档的完整 Markdown 内容")
async def get_document_content(
    doc_id: str,
    svc: LocalWikiService = Depends(get_service),
):
    """获取文档纯文本内容。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"doc_id": doc_id, "content": doc.get("content", ""), "version": doc["version"]}


@router.put("/{doc_id}/content", operation_id="update_document_content", summary="更新文档的 Markdown 内容(乐观锁版本控制)")
async def update_document_content(
    doc_id: str,
    body: DocumentContentUpdate,
    svc: LocalWikiService = Depends(get_service),
):
    """更新文档内容（乐观锁）。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if body.expected_version and doc["version"] != body.expected_version:
        raise HTTPException(
            status_code=409,
            detail=f"Version conflict: expected {body.expected_version}, got {doc['version']}",
        )

    # 更新内容 + 重新计算 hash
    import hashlib
    content_hash = hashlib.sha256(body.content.encode()).hexdigest()

    ok = await svc.update_document(
        doc_id, doc["version"],
        content=body.content,
        content_hash=content_hash,
        status="pending",  # 标记为待重新处理
    )

    if not ok:
        raise HTTPException(status_code=409, detail="Update failed (concurrent modification)")

    return {"status": "ok", "doc_id": doc_id}


@router.patch("/{doc_id}", operation_id="update_document_metadata", summary="更新文档元数据(标题、标签等)")
async def update_document(
    doc_id: str,
    body: DocumentUpdateRequest,
    svc: LocalWikiService = Depends(get_service),
):
    """更新文档元数据。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    update_fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_fields:
        return {"status": "ok", "doc_id": doc_id}

    ok = await svc.update_document(doc_id, doc["version"], **update_fields)
    if not ok:
        raise HTTPException(status_code=409, detail="Update failed")

    return {"status": "ok", "doc_id": doc_id}


@router.delete("/{doc_id}", operation_id="delete_document", summary="删除文档及其关联数据")
async def delete_document(
    doc_id: str,
    svc: LocalWikiService = Depends(get_service),
):
    """删除文档（软删除：status → deleted）。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    ok = await svc.delete_document(doc_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Delete failed")

    return {"status": "ok", "doc_id": doc_id}


@router.post("/bulk-delete")
async def bulk_delete(
    body: BulkDeleteRequest,
    svc: LocalWikiService = Depends(get_service),
):
    """批量删除文档。"""
    deleted = 0
    for doc_id in body.doc_ids:
        try:
            if await svc.delete_document(doc_id):
                deleted += 1
        except Exception:
            pass
    return {"status": "ok", "deleted": deleted, "total": len(body.doc_ids)}


# ── 引用关系 ──────────────────────────────────────────

@router.get("/{doc_id}/references", operation_id="get_document_references", summary="获取文档的引用关系(出边 cites/links_to + 入边被引用)")
async def get_document_references(
    doc_id: str,
    svc: LocalWikiService = Depends(get_service),
):
    """获取文档的引用关系。

    返回:
      outgoing: 本文引用/链接的目标文档(本文为 source)
      incoming: 引用/链接本文的源文档(本文为 target)
    每条带: id, title, filename, source_kind, relative_path, type(cites/links_to), page
    """
    ws_id = find_valid_workspace(svc)
    if not ws_id:
        return {"outgoing": [], "incoming": []}
    db = await svc._get_db(ws_id)

    # 出边：本文 → 别人
    cur = await db.execute(
        """SELECT r.reference_type, r.page, d.id, d.title, d.filename,
                  d.source_kind, d.relative_path
           FROM document_references r
           JOIN documents d ON r.target_document_id = d.id
           WHERE r.source_document_id = ?
           ORDER BY r.reference_type, d.title""",
        (doc_id,),
    )
    outgoing = [
        {
            "id": r[2], "title": r[3] or r[4], "filename": r[4],
            "source_kind": r[5], "relative_path": r[6],
            "type": r[0], "page": r[1],
        }
        for r in await cur.fetchall()
    ]

    # 入边：别人 → 本文
    cur = await db.execute(
        """SELECT r.reference_type, r.page, d.id, d.title, d.filename,
                  d.source_kind, d.relative_path
           FROM document_references r
           JOIN documents d ON r.source_document_id = d.id
           WHERE r.target_document_id = ?
           ORDER BY r.reference_type, d.title""",
        (doc_id,),
    )
    incoming = [
        {
            "id": r[2], "title": r[3] or r[4], "filename": r[4],
            "source_kind": r[5], "relative_path": r[6],
            "type": r[0], "page": r[1],
        }
        for r in await cur.fetchall()
    ]

    return {"outgoing": outgoing, "incoming": incoming}


# ── 高亮管理 ──────────────────────────────────────────

@router.get("/{doc_id}/highlights", operation_id="get_highlights", summary="获取文档的全部高亮标注")
async def get_highlights(
    doc_id: str,
    svc: LocalWikiService = Depends(get_service),
):
    """获取文档的全部高亮。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        highlights = json.loads(doc.get("highlights", "[]"))
    except json.JSONDecodeError:
        highlights = []
    return {"doc_id": doc_id, "highlights": highlights, "version": doc["version"]}


@router.post("/{doc_id}/highlights", operation_id="upsert_highlight", summary="添加或更新单个高亮标注")
async def upsert_highlight(
    doc_id: str,
    body: HighlightUpsert,
    svc: LocalWikiService = Depends(get_service),
):
    """添加或更新单个高亮。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        old_highlights = json.loads(doc.get("highlights", "[]"))
    except json.JSONDecodeError:
        old_highlights = []

    # upsert: 同 ID 则覆盖
    new_highlights = list(old_highlights)
    found = False
    for i, h in enumerate(new_highlights):
        if h.get("id") == body.highlight_id:
            new_highlights[i] = body.data
            found = True
            break
    if not found:
        body.data["id"] = body.highlight_id
        new_highlights.append(body.data)

    ok = await svc.update_document(
        doc_id, doc["version"],
        highlights=json.dumps(new_highlights, ensure_ascii=False),
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Update failed")

    # 同步 chunk 物化内容 → FTS5 索引感知高亮注释
    await svc.sync_highlight_chunks(doc_id, old_highlights, new_highlights)

    return {"status": "ok", "doc_id": doc_id, "highlight_id": body.highlight_id}


@router.patch("/{doc_id}/highlights")
async def replace_highlights(
    doc_id: str,
    body: HighlightsReplace,
    svc: LocalWikiService = Depends(get_service),
):
    """批量替换全部高亮。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        old_highlights = json.loads(doc.get("highlights", "[]"))
    except json.JSONDecodeError:
        old_highlights = []

    ok = await svc.update_document(
        doc_id, doc["version"],
        highlights=json.dumps(body.highlights, ensure_ascii=False),
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Update failed")

    await svc.sync_highlight_chunks(doc_id, old_highlights, body.highlights)

    return {"status": "ok", "doc_id": doc_id, "count": len(body.highlights)}


@router.delete("/{doc_id}/highlights/{highlight_id}", operation_id="delete_highlight", summary="删除单个高亮标注")
async def delete_highlight(
    doc_id: str,
    highlight_id: str,
    svc: LocalWikiService = Depends(get_service),
):
    """删除单个高亮。"""
    doc = await svc.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        old_highlights = json.loads(doc.get("highlights", "[]"))
    except json.JSONDecodeError:
        old_highlights = []

    new_highlights = [h for h in old_highlights if h.get("id") != highlight_id]

    ok = await svc.update_document(
        doc_id, doc["version"],
        highlights=json.dumps(new_highlights, ensure_ascii=False),
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Update failed")

    await svc.sync_highlight_chunks(doc_id, old_highlights, new_highlights)

    return {"status": "ok", "doc_id": doc_id, "highlight_id": highlight_id}


# ── 创建笔记 ──────────────────────────────────────────

@router.post("/note", operation_id="create_note", summary="在 wiki/ 中创建新笔记页面 — Agent 写知识的核心入口")
async def create_note(
    body: CreateNoteRequest,
    svc: LocalWikiService = Depends(get_service),
):
    """创建笔记（无需上传文件，直接提供内容）。

    自动写入 wiki/ 目录并索引。
    """
    from deps import find_valid_workspace
    from pathlib import Path
    from domain.watcher import mark_written, _now_iso

    ws_id = find_valid_workspace(svc)
    if not ws_id:
        raise HTTPException(status_code=400, detail="No workspace found")

    entry = svc._registry.get(ws_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace = Path(entry["path"])

    # 确保路径在 wiki 下
    safe_path = body.path.strip("/")
    if not safe_path.startswith("wiki/"):
        safe_path = "wiki/" + safe_path.lstrip("/")

    target_dir = workspace / safe_path
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / body.filename
    relative_path = str(file_path.relative_to(workspace)).replace("\\", "/")

    # 写入文件
    mark_written(str(file_path))
    file_path.write_text(body.content, encoding="utf-8")

    import hashlib
    content_hash = hashlib.sha256(body.content.encode()).hexdigest()

    doc_id = await svc.create_document(
        ws_id=ws_id,
        user_id="local-user",
        filename=body.filename,
        title=body.title or body.filename,
        path=f"/wiki/",
        relative_path=relative_path,
        source_kind="wiki",
        file_type="md",
        file_size=len(body.content),
        status="ready",
        content=body.content,
        content_hash=content_hash,
        last_indexed_at=_now_iso(),
    )

    return {"status": "ok", "doc_id": doc_id, "filename": body.filename}
