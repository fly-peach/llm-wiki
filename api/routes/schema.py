"""Schema API

- GET  /v1/schema             获取 SCHEMA.md 内容
- PUT  /v1/schema             更新 SCHEMA.md 内容
- GET  /v1/schema/templates   列出实体模板
- GET  /v1/schema/templates/{type}  获取指定模板
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from deps import find_valid_workspace, get_service
from services.local import LocalWikiService
from services.schema import ENTITY_TYPES, get_template

router = APIRouter(prefix="/v1/schema", tags=["schema"])


class SchemaUpdate(BaseModel):
    content: str


@router.get("")
async def get_schema(
    svc: LocalWikiService = Depends(get_service),
):
    """获取当前工作区的 SCHEMA.md 内容。"""
    ws_id = find_valid_workspace(svc)
    if not ws_id:
        raise HTTPException(status_code=400, detail="No workspace found")

    entry = svc._registry.get(ws_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace = Path(entry["path"])
    schema_path = workspace / "SCHEMA.md"

    if not schema_path.exists():
        from services.schema import generate_schema_md
        content = generate_schema_md()
    else:
        content = schema_path.read_text(encoding="utf-8")

    return {"content": content, "path": str(schema_path)}


@router.put("")
async def update_schema(
    body: SchemaUpdate,
    svc: LocalWikiService = Depends(get_service),
):
    """更新 SCHEMA.md 内容。"""
    ws_id = find_valid_workspace(svc)
    if not ws_id:
        raise HTTPException(status_code=400, detail="No workspace found")

    entry = svc._registry.get(ws_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Workspace not found")

    workspace = Path(entry["path"])
    schema_path = workspace / "SCHEMA.md"
    schema_path.write_text(body.content, encoding="utf-8")

    return {"status": "ok", "path": str(schema_path)}


@router.get("/templates")
async def list_templates():
    """列出所有实体模板类型。"""
    return {
        "types": [
            {"key": k, "label": v["label"], "folder": v["folder"]}
            for k, v in ENTITY_TYPES.items()
        ]
    }


@router.get("/templates/{entity_type}")
async def get_entity_template(entity_type: str):
    """获取指定实体类型的 Markdown 模板。"""
    template = get_template(entity_type)
    if not template:
        raise HTTPException(status_code=404, detail=f"Unknown entity type: {entity_type}")
    return {"type": entity_type, "template": template}
