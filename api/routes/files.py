"""文件服务 API

- GET /v1/files/{file_path:path}  直接提供工作区文件的下载/访问
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from deps import find_valid_workspace, get_service
from services.local import LocalWikiService

router = APIRouter(prefix="/v1", tags=["files"])


@router.get("/files/{file_path:path}")
async def serve_file(
    file_path: str,
    svc: LocalWikiService = Depends(get_service),
):
    """直接提供工作区中的文件（raw/wiki 目录下的任意文件）。

    支持 Range 请求（大文件断点续传）。
    """
    ws_id = find_valid_workspace(svc)
    if not ws_id:
        raise HTTPException(status_code=400, detail="No workspace found")

    entry = svc._registry.get(ws_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace = Path(entry["path"])
    full_path = (workspace / file_path).resolve()

    # 安全检查：确保在 workspace 内
    if not str(full_path).startswith(str(workspace.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    # 推断 MIME 类型
    media_type = _guess_mime(full_path.suffix)

    return FileResponse(
        str(full_path),
        media_type=media_type,
        filename=full_path.name,
    )


def _guess_mime(suffix: str) -> str | None:
    """根据扩展名推断 MIME 类型。"""
    mime_map = {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".html": "text/html",
        ".css": "text/css",
        ".js": "application/javascript",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
    }
    return mime_map.get(suffix.lower())
