"""FastAPI 依赖注入

提供所有路由共享的依赖项，如数据库连接、服务实例等。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextvars import ContextVar
from pathlib import Path

from config import settings
from services.base import WikiService
from services.local import LocalWikiService


# 全局单例（开发阶段使用本地模式）
_service: LocalWikiService | None = None

# 前端可显式设置的"当前工作区"，优先于 find_valid_workspace 的"第一个有效"。
# MCP 通过 set_current_workspace tool、前端通过 PUT /v1/workspaces/current 切换。
_current_ws_id: str = ""

# 每请求"锁定工作区"（由 /mcp/{ws_id} 端点注入到 contextvar）。
# 锁定后 find_valid_workspace 只返回该工作区，set_current_workspace 切换被拒绝。
# 与 _current_ws_id 不同：锁定是每请求的（contextvar），客户端配 /mcp/{ws_id} 即硬隔离。
_locked_ws_id: ContextVar[str] = ContextVar("_locked_ws_id", default="")


def set_current_workspace(ws_id: str) -> None:
    """设置当前工作区（前端切换工作区时调用）。"""
    global _current_ws_id
    _current_ws_id = ws_id


def get_current_workspace() -> str:
    """返回前端设置的当前工作区 ID（未设置则空串）。"""
    return _current_ws_id


def set_locked_workspace(ws_id: str):
    """设置当前请求锁定的工作区（/mcp/{ws_id} 端点调用）。返回 token 用于重置。"""
    return _locked_ws_id.set(ws_id)


def reset_locked_workspace(token) -> None:
    """重置锁定工作区到 set 前的状态。"""
    _locked_ws_id.reset(token)


def get_locked_workspace() -> str:
    """返回当前请求锁定的工作区 ID（未锁定则空串）。"""
    return _locked_ws_id.get()


def get_service() -> LocalWikiService:
    """获取全局 Wiki 服务实例（Lazy 初始化）。"""
    global _service
    if _service is None:
        # 注册表文件存放在项目后端的数据目录下
        registry_path = Path(settings.data_dir) / "workspaces.json"
        _service = LocalWikiService(registry_path=registry_path)
    return _service


async def get_wiki_service() -> AsyncGenerator[WikiService, None]:
    """FastAPI Depends：注入 Wiki 服务实例。"""
    svc = get_service()
    try:
        yield svc
    finally:
        pass  # 连接由 close() 管理，路由不负责关闭


async def reset_service() -> None:
    """测试用：重置服务实例。"""
    global _service
    if _service:
        await _service.close()
        _service = None


def _ws_db_exists(svc: LocalWikiService, ws_id: str) -> bool:
    """工作区已注册且其 index.db 存在。"""
    entry = svc._registry.get(ws_id)
    if not entry:
        return False
    return (Path(entry["path"]) / ".llmwiki" / "index.db").exists()


def find_valid_workspace(svc: LocalWikiService) -> str:
    """找到数据库文件存在的已注册工作区 ID。

    优先级：
      1. 锁定工作区（/mcp/{ws_id} 端点注入，硬锁定到该工作区）
      2. 全局"当前工作区"（set_current_workspace 设置，MCP/前端切换时写入）
      3. 注册表中第一个 DB 存在的工作区
    返回空字符串表示无有效工作区。
    """
    locked = _locked_ws_id.get()
    if locked and _ws_db_exists(svc, locked):
        return locked
    if _current_ws_id and _ws_db_exists(svc, _current_ws_id):
        return _current_ws_id
    for entry in svc._registry.list_all():
        if (Path(entry["path"]) / ".llmwiki" / "index.db").exists():
            return entry["id"]
    return ""
