"""工作区管理 API

- POST /v1/workspaces        创建/注册工作区
- GET  /v1/workspaces        列出所有工作区
- GET  /v1/workspaces/{id}   获取工作区详情
- DELETE /v1/workspaces/{id} 注销工作区
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import find_valid_workspace, get_current_workspace, get_service, set_current_workspace
from domain.watcher import watch_workspace
from infra.workspace.registry import WorkspaceEntry
from services.local import LocalWikiService

router = APIRouter(prefix="/v1/workspaces", tags=["workspaces"])

# 运行中的 watcher 任务: ws_id -> asyncio.Task
_watcher_tasks: dict[str, asyncio.Task] = {}


class CreateWorkspaceRequest(BaseModel):
    path: str
    name: str | None = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    path: str
    kind: str
    created_at: str


@router.post("", response_model=WorkspaceResponse, operation_id="create_workspace", summary="创建并初始化新的工作区(知识库)")
async def create_workspace(
    body: CreateWorkspaceRequest,
    svc: LocalWikiService = Depends(get_service),
):
    """创建并初始化工作区，自动启动文件监控。"""
    ws_path = Path(body.path).resolve()

    # 检查是否已注册
    existing = svc._registry.get_by_path(str(ws_path))
    if existing:
        # 返回已有工作区
        ws = await svc.get_workspace(existing["id"])
        if ws:
            return WorkspaceResponse(
                id=ws["id"], name=ws["name"],
                path=existing["path"], kind=ws["kind"],
                created_at=ws["created_at"],
            )
        # 注册表条目已失效（id 与 DB 实际行不一致，通常由历史 bug 残留）：
        # 注销失效条目并取消其 watcher，随后走重新初始化流程。
        stale_task = _watcher_tasks.pop(existing["id"], None)
        if stale_task:
            stale_task.cancel()
        svc._registry.unregister(existing["id"])

    # 初始化
    ws_id = await svc.init_workspace(ws_path)

    # 启动文件监控
    stop_event = asyncio.Event()
    task = asyncio.create_task(
        watch_workspace(svc, ws_id, ws_path, stop_event)
    )
    _watcher_tasks[ws_id] = task

    ws = await svc.get_workspace(ws_id)
    if not ws:
        raise HTTPException(
            status_code=500,
            detail=f"Workspace initialized but could not be loaded: {ws_id}",
        )
    return WorkspaceResponse(
        id=ws_id, name=ws["name"],
        path=str(ws_path), kind=ws["kind"],
        created_at=ws["created_at"],
    )


@router.get("", response_model=list[WorkspaceResponse], operation_id="list_workspaces", summary="列出所有已注册的工作区(知识库)")
async def list_workspaces(
    svc: LocalWikiService = Depends(get_service),
):
    """列出所有已注册的工作区。"""
    entries = svc._registry.list_all()
    result = []
    for entry in entries:
        try:
            ws = await svc.get_workspace(entry["id"])
            if ws:
                result.append(WorkspaceResponse(
                    id=ws["id"], name=ws["name"],
                    path=entry["path"], kind=ws["kind"],
                    created_at=ws["created_at"],
                ))
        except Exception:
            pass
    return result


class SetCurrentRequest(BaseModel):
    ws_id: str


@router.put("/current", operation_id="set_current_workspace", summary="设置当前工作区(前端切换工作区时调用)")
async def set_current(
    body: SetCurrentRequest,
    svc: LocalWikiService = Depends(get_service),
):
    """设置当前工作区。后续所有依赖 find_valid_workspace 的请求优先使用它。"""
    entry = svc._registry.get(body.ws_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not (Path(entry["path"]) / ".llmwiki" / "index.db").exists():
        raise HTTPException(status_code=400, detail="Workspace DB not found")
    set_current_workspace(body.ws_id)
    return {"status": "ok", "ws_id": body.ws_id}


@router.get("/current", operation_id="get_current_workspace", summary="获取当前工作区 ID(未设置则回退到第一个有效工作区)")
async def get_current(
    svc: LocalWikiService = Depends(get_service),
):
    """获取当前工作区 ID。"""
    cur = get_current_workspace() or find_valid_workspace(svc)
    return {"ws_id": cur}


@router.get("/{ws_id}", response_model=WorkspaceResponse)
async def get_workspace(
    ws_id: str,
    svc: LocalWikiService = Depends(get_service),
):
    """获取单个工作区详情。"""
    entry = svc._registry.get(ws_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Workspace not found")
    ws = await svc.get_workspace(ws_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace data not found")
    return WorkspaceResponse(
        id=ws["id"], name=ws["name"],
        path=entry["path"], kind=ws["kind"],
        created_at=ws["created_at"],
    )


@router.delete("/{ws_id}")
async def delete_workspace(
    ws_id: str,
    svc: LocalWikiService = Depends(get_service),
):
    """注销工作区（不删除磁盘文件）。"""
    entry = svc._registry.get(ws_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # 停止 watcher
    task = _watcher_tasks.pop(ws_id, None)
    if task:
        task.cancel()

    # 若注销的是当前工作区，清空当前工作区标记，避免指向已失效工作区
    if get_current_workspace() == ws_id:
        set_current_workspace("")

    svc._registry.unregister(ws_id)
    return {"status": "ok", "message": f"Workspace {ws_id} unregistered"}
