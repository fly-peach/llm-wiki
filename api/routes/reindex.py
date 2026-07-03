"""重建索引 API

- POST /v1/reindex  扫描工作区全部文件并重建索引

用于首次初始化后的全量索引，或修复索引不一致。
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from deps import find_valid_workspace, get_service
from domain.file_types import SIMPLE_TEXT, EXTRACTION, infer_source_kind
from domain.watcher import _index_file, _should_ignore
from services.local import LocalWikiService

router = APIRouter(prefix="/v1", tags=["reindex"])


@router.post("/reindex")
async def reindex_workspace(
    ws_id: str = "",
    svc: LocalWikiService = Depends(get_service),
):
    """扫描工作区文件系统，重建全部索引。

    这是一个同步操作（对小型工作区），大型工作区建议使用后台任务。
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

    return {
        "status": "ok",
        "workspace_id": ws_id,
        "indexed": indexed,
        "skipped": skipped,
        "errors": errors,
    }
