"""文件上传 API

- POST /v1/upload  上传文件到工作区
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from deps import find_valid_workspace, get_service
from domain.file_types import EXTRACTION, infer_source_kind, is_simple_text
from domain.watcher import mark_written
from services.local import LocalWikiService

router = APIRouter(prefix="/v1", tags=["upload"])


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    path: str = Form(default="/"),
    ws_id: str = Form(default=""),
    svc: LocalWikiService = Depends(get_service),
):
    """上传文件到工作区并自动索引。

    参数:
        file: 上传的文件
        path: 目标子目录（默认 /，即工作区根目录）
        ws_id: 工作区 ID（若为空则用第一个已注册工作区）

    流程:
        1. 确定工作区 → 写入磁盘 → mark_written
        2. 索引到 documents 表
        3. 返回 doc_id
    """
    # 确定工作区
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

    # 构建目标路径
    dir_path = path.strip("/").replace("\\", "/")
    if not dir_path.endswith("/"):
        dir_path += "/"
    target_dir = workspace / dir_path
    target_dir.mkdir(parents=True, exist_ok=True)

    # 写入文件
    filename = file.filename or "unnamed"
    dest = target_dir / filename

    content_bytes = await file.read()

    # 防回环
    mark_written(str(dest))
    dest.write_bytes(content_bytes)

    # 索引
    relative_path = str(dest.relative_to(workspace)).replace("\\", "/")
    extension = dest.suffix.lstrip(".").lower()
    source_kind = infer_source_kind(relative_path)

    content: str | None = None
    content_hash: str | None = None

    if is_simple_text(extension):
        try:
            content = content_bytes.decode("utf-8")
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            status = "ready"
        except UnicodeDecodeError:
            content = None
            status = "pending"
    elif extension in EXTRACTION:
        status = "pending"
    else:
        status = "pending"

    from domain.watcher import _now_iso
    now = _now_iso()

    doc_id = await svc.create_document(
        ws_id=ws_id,
        user_id="local-user",
        filename=filename,
        title=filename,
        path=f"/{source_kind}/",
        relative_path=relative_path,
        source_kind=source_kind,
        file_type=extension,
        file_size=len(content_bytes),
        status=status,
        content=content or "",
        content_hash=content_hash or "",
        last_indexed_at=now,
    )

    return {
        "status": "ok",
        "doc_id": doc_id,
        "filename": filename,
        "relative_path": relative_path,
        "source_kind": source_kind,
    }
