"""全文搜索 API

- GET /v1/search  FTS5 全文搜索
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from deps import find_valid_workspace, get_service
from services.local import LocalWikiService

router = APIRouter(prefix="/v1", tags=["search"])


@router.get("/search", operation_id="search_documents", summary="全文搜索文档内容(FTS5)")
async def search(
    query: str = Query(..., min_length=1, description="搜索关键词"),
    limit: int = Query(default=20, ge=1, le=100),
    annotated_only: bool = Query(default=False, description="仅搜索含高亮标注的块"),
    svc: LocalWikiService = Depends(get_service),
):
    """全文搜索文档块。

    使用 SQLite FTS5，按相关性排序返回匹配的文档块。
    返回格式:
    ```
    [
      {
        "doc_id": "...",
        "filename": "note.md",
        "title": "Note",
        "chunk_index": 0,
        "chunk_content": "匹配的文本片段...",
        "header_breadcrumb": "研究 > ML",
        "token_count": 128
      }
    ]
    ```
    """
    ws_id = find_valid_workspace(svc)
    if not ws_id:
        return {"results": [], "query": query, "total": 0}

    results = await svc.search(ws_id, query, limit, annotated_only=annotated_only)
    return {
        "results": [
            {
                "doc_id": r["id"],
                "filename": r["filename"],
                "title": r.get("title", ""),
                "source_kind": r.get("source_kind", ""),
                "chunk_index": r.get("chunk_index"),
                "chunk_content": r.get("chunk_content", ""),
                "header_breadcrumb": r.get("header_breadcrumb", ""),
                "token_count": r.get("token_count", 0),
            }
            for r in results
        ],
        "query": query,
        "total": len(results),
    }
