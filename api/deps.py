"""FastAPI 依赖注入

提供所有路由共享的依赖项，如数据库连接、服务实例等。
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from config import settings
from services.base import WikiService
from services.local import LocalWikiService


# 全局单例（开发阶段使用本地模式）
_service: LocalWikiService | None = None

# 前端可显式设置的"当前工作区"，优先于 find_valid_workspace 的"第一个有效"
_current_ws_id: str = ""


def set_current_workspace(ws_id: str) -> None:
    """设置当前工作区（前端切换工作区时调用）。"""
    global _current_ws_id
    _current_ws_id = ws_id


def get_current_workspace() -> str:
    """返回前端设置的当前工作区 ID（未设置则空串）。"""
    return _current_ws_id


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


def find_valid_workspace(svc: LocalWikiService) -> str:
    """找到第一个数据库文件存在的已注册工作区 ID。

    若前端设置了"当前工作区"且其 DB 仍存在，则优先返回它；
    否则遍历注册表，跳过已删除的过期条目。
    返回空字符串表示无有效工作区。
    """
    if _current_ws_id:
        entry = svc._registry.get(_current_ws_id)
        if entry:
            db_path = Path(entry["path"]) / ".llmwiki" / "index.db"
            if db_path.exists():
                return _current_ws_id
    for entry in svc._registry.list_all():
        db_path = Path(entry["path"]) / ".llmwiki" / "index.db"
        if db_path.exists():
            return entry["id"]
    return ""
