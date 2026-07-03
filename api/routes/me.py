"""用户信息 + 用量统计 API

- GET /v1/me      当前用户信息
- GET /v1/usage   数据库用量统计
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from deps import find_valid_workspace, get_service
from services.local import LocalWikiService

router = APIRouter(prefix="/v1", tags=["me"])


@router.get("/me")
async def me(
    svc: LocalWikiService = Depends(get_service),
):
    """当前用户信息。"""
    entries = svc._registry.list_all()
    return {
        "user_id": "local-user",
        "workspaces": len(entries),
    }


@router.get("/usage")
async def usage(
    svc: LocalWikiService = Depends(get_service),
):
    """数据库用量统计 — 分类计数 + 状态计数 + 实体分布 + 最近活动。"""
    ws_id = find_valid_workspace(svc)
    if not ws_id:
        return {
            "documents": 0, "wiki_pages": 0, "raw_files": 0, "assets": 0,
            "by_status": {}, "by_entity": [], "recent": [],
        }

    db = await svc._get_db(ws_id)

    # 按 source_kind 计数
    by_kind = {"wiki": 0, "raw": 0, "asset": 0}
    cur = await db.execute(
        "SELECT source_kind, COUNT(*) FROM documents GROUP BY source_kind"
    )
    for r in await cur.fetchall():
        by_kind[r[0]] = r[1]

    # 按 status 计数
    by_status: dict[str, int] = {}
    cur = await db.execute(
        "SELECT status, COUNT(*) FROM documents GROUP BY status"
    )
    for r in await cur.fetchall():
        by_status[r[0] or "unknown"] = r[1]

    # 实体类型分布
    cur = await db.execute(
        """SELECT COALESCE(entity_type, '') AS et, COUNT(*) AS c
           FROM documents WHERE entity_type IS NOT NULL AND entity_type != ''
           GROUP BY entity_type ORDER BY c DESC"""
    )
    by_entity = [{"entity_type": r[0], "count": r[1]} for r in await cur.fetchall()]

    # 最近活动（updated_at desc top 8）
    cur = await db.execute(
        """SELECT id, title, filename, source_kind, status, updated_at
           FROM documents ORDER BY updated_at DESC LIMIT 8"""
    )
    recent = [
        {
            "id": r[0], "title": r[1] or r[2], "filename": r[2],
            "source_kind": r[3], "status": r[4], "updated_at": r[5],
        }
        for r in await cur.fetchall()
    ]

    return {
        "documents": by_kind["wiki"] + by_kind["raw"] + by_kind["asset"],
        "wiki_pages": by_kind["wiki"],
        "raw_files": by_kind["raw"],
        "assets": by_kind["asset"],
        "by_status": by_status,
        "by_entity": by_entity,
        "recent": recent,
    }
