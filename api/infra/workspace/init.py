"""工作区初始化

幂等地初始化工作区目录结构、数据库和种子页面。
"""

from __future__ import annotations

import uuid
from pathlib import Path

from infra.db.sqlite import create_pool, execute_schema


# 本地单用户模式使用的默认 user_id
LOCAL_USER_ID = "local-user"


async def init_workspace(workspace: Path) -> str:
    """幂等地初始化工作区。

    1. 创建目录结构（wiki/、.llmwiki/）
    2. 执行 SQLite schema
    3. 注册 workspace 行
    4. 创建种子 wiki 页面（overview、index、log）

    参数:
        workspace: 工作区根目录路径

    返回:
        工作区 ID（uuid）
    """
    # ── 1. 目录结构 ──────────────────────────────────────
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "wiki").mkdir(exist_ok=True)
    dot_dir = workspace / ".llmwiki"
    dot_dir.mkdir(exist_ok=True)
    (dot_dir / "cache").mkdir(exist_ok=True)

    # ── 2. 数据库 + Schema ──────────────────────────────
    db_path = dot_dir / "index.db"
    db = await create_pool(db_path)

    schema_path = Path(__file__).parent.parent.parent.parent / "shared" / "sqlite_schema.sql"
    await execute_schema(db, schema_path)

    # ── 3. 注册 workspace ───────────────────────────────
    # 幂等：重新初始化同一目录时 DB 中可能已存在 workspace 行。
    # workspace 表有 UNIQUE(user_id) 约束，且本地模式固定使用 LOCAL_USER_ID，
    # 若仍用 INSERT OR IGNORE + 新 uuid，新行会被静默丢弃，导致返回的 ws_id
    # 与表中实际行的 id 不一致（后续 get_workspace 返回 None）。故先查既有行并复用其 id。
    cursor = await db.execute(
        "SELECT id FROM workspace WHERE user_id = ?", (LOCAL_USER_ID,)
    )
    row = await cursor.fetchone()
    if row:
        ws_id = row[0]
    else:
        ws_id = str(uuid.uuid4())
        await db.execute(
            """INSERT INTO workspace (id, name, description, kind, user_id)
               VALUES (?, ?, '', 'wiki', ?)""",
            (ws_id, workspace.name, LOCAL_USER_ID),
        )
        await db.commit()

    # ── 4. 种子 wiki 页面 ───────────────────────────────
    wiki_dir = workspace / "wiki"

    overview = wiki_dir / "overview.md"
    if not overview.exists():
        overview.write_text(
            f"# {workspace.name} — Overview\n\n"
            "> 这是知识库的总览页面。LLM 会在此汇总核心概念与关键结论。\n\n"
            "## 快速导航\n\n"
            "- 查看 [index.md](index.md) 了解全部内容索引\n"
            "- 查看 [log.md](log.md) 了解最近操作记录\n",
            encoding="utf-8",
        )

    index_md = wiki_dir / "index.md"
    if not index_md.exists():
        index_md.write_text(
            "# Wiki 内容索引\n\n"
            "> 此文件由 LLM 自动维护，按分类列出所有 wiki 页面。\n\n"
            "## 实体\n\n"
            "（待填充）\n\n"
            "## 摘要\n\n"
            "（待填充）\n\n"
            "## 对比分析\n\n"
            "（待填充）\n\n"
            "## 综述\n\n"
            "（待填充）\n\n"
            "## 主题\n\n"
            "（待填充）\n",
            encoding="utf-8",
        )

    log_md = wiki_dir / "log.md"
    if not log_md.exists():
        log_md.write_text(
            "# 操作日志\n\n"
            f"> 记录每次 LLM 对 wiki 的修改操作。\n\n"
            f"| 时间 | 操作 | 目标 |\n"
            f"|------|------|------|\n"
            f"| {_now_iso()} | init | 工作区初始化 |\n",
            encoding="utf-8",
        )

    await db.close()
    return ws_id


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
