"""知识图谱 API

- GET  /v1/graph          获取图谱数据 {nodes, edges}
- POST /v1/graph/rebuild  全量重建图谱
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from deps import find_valid_workspace, get_service
from services.graph import get_graph, rebuild_graph
from services.local import LocalWikiService

router = APIRouter(prefix="/v1", tags=["graph"])


@router.get("/graph", operation_id="get_graph", summary="获取知识图谱数据(节点+边),查看文档间引用关系")
async def graph_get(
    svc: LocalWikiService = Depends(get_service),
):
    """获取知识图谱数据。

    返回节点列表和边列表，格式适合前端可视化。
    """
    ws_id = find_valid_workspace(svc)
    if not ws_id:
        return {"nodes": [], "edges": [], "stats": {"node_count": 0, "edge_count": 0}}

    return await get_graph(svc, ws_id)


@router.post("/graph/rebuild", operation_id="rebuild_graph", summary="全量重建知识图谱(扫描 wiki 页面重新提取引用)")
async def graph_rebuild(
    svc: LocalWikiService = Depends(get_service),
):
    """全量重建知识图谱。

    扫描所有 wiki 页面内容，解析引用关系，
    原子性替换 document_references 表中的全部边。
    """
    ws_id = find_valid_workspace(svc)
    if not ws_id:
        raise HTTPException(status_code=400, detail="No workspace found")

    result = await rebuild_graph(svc, ws_id)
    return {
        "status": "ok",
        "citations": result["citations"],
        "links": result["links"],
        "errors": result["errors"],
    }
