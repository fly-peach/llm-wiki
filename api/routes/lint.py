"""Lint 健康检查 API

- POST /v1/lint  运行全部 8 条 lint 规则
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from deps import find_valid_workspace, get_service
from services.lint import run_all_lint
from services.local import LocalWikiService

router = APIRouter(prefix="/v1", tags=["lint"])


@router.post("/lint", operation_id="run_lint", summary="运行 Lint 健康检查规则")
async def run_lint(
    svc: LocalWikiService = Depends(get_service),
):
    """运行全部 lint 健康检查规则。

    返回包含 summary（按严重度统计）和 issues（具体问题列表）的报告。
    """
    ws_id = find_valid_workspace(svc)
    if not ws_id:
        raise HTTPException(status_code=400, detail="No workspace found")

    return await run_all_lint(svc, ws_id)
