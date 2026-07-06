"""LLM Wiki API — FastAPI 应用入口"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse

from deps import (
    _ws_db_exists,
    find_valid_workspace,
    get_service,
    reset_locked_workspace,
    reset_service,
    set_locked_workspace,
)
from routes.workspaces import router as workspaces_router, _watcher_tasks
from routes.upload import router as upload_router
from routes.reindex import router as reindex_router
from routes.search import router as search_router
from routes.graph import router as graph_router
from routes.documents import router as documents_router
from routes.files import router as files_router
from routes.me import router as me_router
from routes.schema import router as schema_router
from routes.lint import router as lint_router
from routes.guide import router as guide_router
from services.local import LocalWikiService
from fastapi_mcp import FastApiMCP


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期：启动时恢复工作区的 watcher，关闭时清理。"""
    # 启动时：可以选择恢复之前注册工作区的监控
    print("[lifespan] LLM Wiki API starting...")
    yield
    # 关闭时：清理所有 watcher 和数据库连接
    print("[lifespan] Shutting down...")
    for task in _watcher_tasks.values():
        task.cancel()
    await reset_service()


app = FastAPI(
    title="LLM Wiki API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──────────────────────────────────────────
app.include_router(workspaces_router)
app.include_router(upload_router)
app.include_router(reindex_router)
app.include_router(search_router)
app.include_router(graph_router)
app.include_router(documents_router)
app.include_router(files_router)
app.include_router(me_router)
app.include_router(schema_router)
app.include_router(lint_router)
app.include_router(guide_router)


# ── 基础端点 ──────────────────────────────────────────

@app.get("/v1/health")
async def health():
    return {"status": "ok", "service": "llmwiki-api"}


@app.get("/v1/documents", operation_id="list_documents", summary="列出工作区中的文档,可按 source_kind(wiki/raw)、status、entity_type 和路径过滤")
async def list_documents(
    source_kind: str | None = Query(default=None),
    path: str | None = Query(default=None),
    status: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    svc: LocalWikiService = Depends(get_service),
):
    """列出已索引的文档。"""
    ws_id = find_valid_workspace(svc)
    if not ws_id:
        return {"documents": [], "total": 0}

    docs = await svc.list_documents(
        ws_id, source_kind=source_kind, path=path, status=status,
        entity_type=entity_type, limit=limit, offset=offset,
    )
    total = await svc.count_documents(
        ws_id, source_kind=source_kind, status=status, entity_type=entity_type,
    )
    return {"documents": docs, "total": total}


@app.post("/v1/process/{doc_id}")
async def process_single(
    doc_id: str,
    svc: LocalWikiService = Depends(get_service),
):
    """手动触发单个文档的处理（提取 + 分块）。"""
    from domain.processor import process_document

    ws_id = find_valid_workspace(svc)
    if not ws_id:
        return {"status": "error", "message": "No workspace found"}

    entry = svc._registry.get(ws_id)
    if not entry:
        return {"status": "error", "message": "Workspace not in registry"}

    workspace = Path(entry["path"])
    ok = await process_document(svc, ws_id, doc_id, workspace)
    return {"status": "ok" if ok else "failed", "doc_id": doc_id}


# ── MCP Server（fastapi-mcp，挂载于 /mcp，复用 REST 路由）──────────
# 必须在所有 include_router / @app 路由定义之后调用：扫描已注册路由生成 tool
MCP_INCLUDE_OPERATIONS = [
    "guide",
    "list_workspaces", "create_workspace",
    "get_current_workspace", "set_current_workspace",
    "list_documents", "get_document", "read_document",
    "create_note", "update_document_content", "update_document_metadata",
    "delete_document",
    "get_highlights", "upsert_highlight", "delete_highlight",
    "search_documents", "get_graph", "rebuild_graph", "run_lint",
]

mcp = FastApiMCP(
    app,
    name="LLM Wiki MCP",
    description="LLM Wiki 知识管理工具集（复用 REST 接口，同进程 ASGI 直连）。"
                "多工作区：先 list_workspaces 查看可用工作区，再用 set_current_workspace 切换。",
    include_operations=MCP_INCLUDE_OPERATIONS,
    headers=["authorization"],
)
mcp.mount_http(mount_path="/mcp")


# ── MCP 锁定端点：/mcp/{ws_id} 硬隔离到指定工作区 ────────────
# 客户端配 /mcp/{ws_id} 即锁定到该工作区：find_valid_workspace 总返回它，
# set_current_workspace 切换被拒绝（403）。与 /mcp（灵活模式，可切换）并存。
_mcp_transport = mcp._http_transport


@app.api_route(
    "/mcp/{ws_id}",
    methods=["GET", "POST", "DELETE"],
    include_in_schema=False,
)
async def mcp_scoped_http(ws_id: str, request: Request):
    """工作区隔离的 MCP 端点。锁定到 ws_id，set_current_workspace 切换被拒绝。"""
    if not _ws_db_exists(get_service(), ws_id):
        raise HTTPException(status_code=404, detail=f"Workspace not found: {ws_id}")
    token = set_locked_workspace(ws_id)
    try:
        return await _mcp_transport.handle_fastapi_request(request)
    finally:
        reset_locked_workspace(token)


# ── 生产模式：挂载前端静态文件 ──────────────────────
# 检测 api/static/ 目录是否存在（由 build_console.py 构建生成）
_static_dir = Path(__file__).parent / "static"
if _static_dir.exists() and (_static_dir / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(_static_dir / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """SPA fallback: 非 API 路径返回 index.html"""
        if full_path.startswith(("v1/", "mcp", "docs", "openapi.json", "redoc")):
            from starlette.responses import Response
            return Response(status_code=404)
        index = _static_dir / "index.html"
        if index.exists():
            return FileResponse(str(index))
        from starlette.responses import Response
        return Response(status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
