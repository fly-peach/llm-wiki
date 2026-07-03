"""知识图谱 — 图重建 + 图查询

- 全量重建：扫描 wiki 页面内容 → 解析引用 → 原子写入 document_references
- 图查询：返回 {nodes, edges} 供可视化
"""

from __future__ import annotations

from typing import Any

from services.references import (
    build_lookup_maps,
    extract_references,
)


async def rebuild_graph(svc, ws_id: str) -> dict[str, int]:
    """全量重建知识图谱（原子操作）。

    流程:
      1. 获取所有文档 → 构建查找映射
      2. 只扫描 wiki 页面（不扫描 raw）
      3. 解析每个 wiki 页面的引用
      4. 原子操作：DELETE 全部边 + 批量 INSERT

    返回: {"citations": N, "links": N, "errors": N}
    """
    db = await svc._get_db(ws_id)

    # ── 1. 获取所有文档 ─────────────────────────────
    all_docs = await svc.list_documents(ws_id, limit=10000)
    filename_map, base_map, wiki_path_map = build_lookup_maps(all_docs)

    # ── 2. 获取 wiki 页面 ────────────────────────────
    wiki_docs = await svc.list_documents(ws_id, source_kind="wiki", limit=10000)

    # ── 3. 解析引用 ──────────────────────────────────
    all_edges: list[dict] = []
    for page in wiki_docs:
        content = page.get("content", "")
        if not content:
            continue
        edges = extract_references(
            content,
            page["id"],
            filename_map,
            base_map,
            wiki_path_map,
        )
        for edge in edges:
            all_edges.append({
                "source_id": page["id"],
                "target_id": edge["target_id"],
                "type": edge["type"],
                "page": edge.get("page"),
            })

    # ── 4. 原子写入 ──────────────────────────────────
    from infra.db.sqlite import serialized_write

    citations = 0
    links = 0
    errors = 0

    async with serialized_write():
        try:
            # 删除全部旧边
            await db.execute("DELETE FROM document_references")

            # 插入新边
            for edge in all_edges:
                try:
                    await db.execute(
                        """INSERT OR IGNORE INTO document_references
                           (source_document_id, target_document_id, reference_type, page)
                           VALUES (?, ?, ?, ?)""",
                        (
                            edge["source_id"],
                            edge["target_id"],
                            edge["type"],
                            edge["page"],
                        ),
                    )
                    if edge["type"] == "cites":
                        citations += 1
                    else:
                        links += 1
                except Exception:
                    errors += 1

            await db.commit()
        except Exception:
            await db.rollback()
            raise

    return {"citations": citations, "links": links, "errors": errors}


async def get_graph(svc, ws_id: str) -> dict[str, Any]:
    """返回知识图谱数据 {nodes, edges} 供前端可视化。

    节点信息包含: id, title, filename, source_kind, file_type, path
    边信息包含: source, target, type, page
    """
    db = await svc._get_db(ws_id)

    # 节点：从 referenced documents 中获取
    cursor = await db.execute(
        """SELECT DISTINCT d.id, d.title, d.filename, d.source_kind,
               d.file_type, d.path, d.status
           FROM documents d
           WHERE d.id IN (
               SELECT source_document_id FROM document_references
               UNION
               SELECT target_document_id FROM document_references
           )
           UNION
           SELECT d.id, d.title, d.filename, d.source_kind,
                  d.file_type, d.path, d.status
           FROM documents d
           WHERE d.source_kind = 'wiki'
           ORDER BY source_kind, title"""
    )
    node_rows = await cursor.fetchall()
    nodes = [
        {
            "id": r[0],
            "title": r[1] or r[2],
            "filename": r[2],
            "source_kind": r[3],
            "file_type": r[4],
            "path": r[5],
            "status": r[6],
        }
        for r in node_rows
    ]

    # 边
    cursor = await db.execute(
        """SELECT source_document_id, target_document_id, reference_type, page
           FROM document_references"""
    )
    edge_rows = await cursor.fetchall()
    edges = [
        {
            "source": r[0],
            "target": r[1],
            "type": r[2],
            "page": r[3],
        }
        for r in edge_rows
    ]

    # 统计
    node_count = len(nodes)
    edge_count = len(edges)
    wiki_count = sum(1 for n in nodes if n["source_kind"] == "wiki")
    raw_count = sum(1 for n in nodes if n["source_kind"] == "raw")

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": node_count,
            "edge_count": edge_count,
            "wiki_nodes": wiki_count,
            "raw_nodes": raw_count,
        },
    }
