"""工作区注册表

使用 JSON 文件持久化工作区列表，支持多工作区管理。
自动检测并清理已删除的工作区条目。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict


class WorkspaceEntry(TypedDict):
    id: str
    name: str
    path: str
    created_at: str


class WorkspaceRegistry:
    """基于 JSON 文件的工作区注册表。

    注册表文件位于 ~/.llmwiki/workspaces.json，记录所有已注册的工作区。
    加载时自动清理磁盘上已不存在的工作区条目。
    """

    def __init__(self, registry_path: str | Path | None = None):
        if registry_path is None:
            registry_path = Path.home() / ".llmwiki" / "workspaces.json"
        self._path = Path(registry_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[WorkspaceEntry]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            entries = data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

        # 自动清理：过滤掉工作区 db 已不存在的条目
        valid: list[WorkspaceEntry] = []
        changed = False
        for entry in entries:
            db_path = Path(entry["path"]) / ".llmwiki" / "index.db"
            if db_path.exists():
                valid.append(entry)
            else:
                changed = True
        if changed:
            self._save(valid)
        return valid

    def _save(self, entries: list[WorkspaceEntry]) -> None:
        self._path.write_text(
            json.dumps(entries, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_all(self) -> list[WorkspaceEntry]:
        return self._load()

    def get(self, ws_id: str) -> WorkspaceEntry | None:
        for entry in self._load():
            if entry["id"] == ws_id:
                return entry
        return None

    def get_by_path(self, path: str) -> WorkspaceEntry | None:
        resolved = str(Path(path).resolve())
        for entry in self._load():
            if str(Path(entry["path"]).resolve()) == resolved:
                return entry
        return None

    def register(self, entry: WorkspaceEntry) -> None:
        entries = self._load()
        # 幂等：同 ID 覆盖
        existing = [e for e in entries if e["id"] != entry["id"]]
        existing.append(entry)
        self._save(existing)

    def unregister(self, ws_id: str) -> bool:
        entries = self._load()
        new_entries = [e for e in entries if e["id"] != ws_id]
        if len(new_entries) == len(entries):
            return False
        self._save(new_entries)
        return True
