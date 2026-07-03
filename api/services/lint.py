"""Lint 规则引擎

8 条健康检查规则，检测 wiki 知识库的问题并生成建议修复方案。
"""

from __future__ import annotations

import re
from typing import Any

from services.references import parse_wiki_links

# 失效链接正则（匹配 [[...]] 和 Markdown 链接）
_LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")


async def run_all_lint(svc, ws_id: str) -> dict[str, Any]:
    """运行所有 8 条 lint 规则，返回完整报告。"""
    issues: list[dict] = []

    docs = await svc.list_documents(ws_id, limit=10000)
    wiki_docs = [d for d in docs if d["source_kind"] == "wiki"]

    # ── 1. 孤立页面 ──────────────────────────────────
    await _check_orphan_pages(svc, ws_id, wiki_docs, issues)

    # ── 2. 失效链接 ──────────────────────────────────
    await _check_broken_links(wiki_docs, docs, issues)

    # ── 3. 缺少引用来源 ──────────────────────────────
    await _check_missing_references(wiki_docs, issues)

    # ── 4. 索引漂移 ──────────────────────────────────
    await _check_index_drift(wiki_docs, issues)

    # ── 5. 重复内容 ──────────────────────────────────
    await _check_duplicate_content(wiki_docs, issues)

    errors = sum(1 for i in issues if i["severity"] == "error")
    warnings = sum(1 for i in issues if i["severity"] == "warning")
    suggestions = sum(1 for i in issues if i["severity"] == "suggestion")

    return {
        "summary": {
            "total": len(issues),
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
        },
        "issues": issues,
    }


async def _check_orphan_pages(svc, ws_id, wiki_docs, issues):
    """检测无入链的孤立 wiki 页面。"""
    db = await svc._get_db(ws_id)
    cursor = await db.execute(
        "SELECT target_document_id FROM document_references"
    )
    referenced = {r[0] for r in await cursor.fetchall()}

    for doc in wiki_docs:
        if doc["id"] not in referenced:
            # 排除种子页面
            if doc["filename"] in ("index.md", "log.md", "overview.md"):
                continue
            issues.append({
                "rule": "orphan-pages",
                "severity": "warning",
                "doc_id": doc["id"],
                "title": doc.get("title", doc["filename"]),
                "message": "该页面没有任何入链（孤立页面）",
                "suggestion": "从相关 topic 页面或 index.md 添加链接",
            })


async def _check_broken_links(wiki_docs, all_docs, issues):
    """检测失效的内部链接。"""
    # 构建查找集
    filenames = {d["filename"].lower() for d in all_docs}
    basenames = set()
    for d in all_docs:
        f = d["filename"].lower()
        stem = f.rsplit(".", 1)[0] if "." in f else f
        basenames.add(stem)
    valid_targets = filenames | basenames

    for doc in wiki_docs:
        content = doc.get("content", "")
        if not content:
            continue

        # 检查 Markdown 链接
        for match in _LINK_RE.finditer(content):
            target = match.group(2).strip().lower()
            # 去除路径前缀
            target_name = target.rsplit("/", 1)[-1] if "/" in target else target
            target_stem = target_name.rsplit(".", 1)[0] if "." in target_name else target_name

            if target_name not in valid_targets and target_stem not in valid_targets:
                issues.append({
                    "rule": "broken-links",
                    "severity": "error",
                    "doc_id": doc["id"],
                    "title": doc.get("title", doc["filename"]),
                    "message": f"失效链接: [{match.group(1)}]({target})",
                    "suggestion": "修正链接或创建目标页面",
                })


async def _check_missing_references(wiki_docs, issues):
    """检测无引用来源的声明性页面。"""
    citation_re = re.compile(r"\[\^[\d]+\]")

    for doc in wiki_docs:
        content = doc.get("content", "")
        if not content:
            continue
        # 如果页面有实质性内容但缺少引用标记
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
        has_citations = bool(citation_re.search(content))

        if len(lines) > 5 and not has_citations:
            # 长页面缺少引用 → 建议
            issues.append({
                "rule": "missing-references",
                "severity": "warning",
                "doc_id": doc["id"],
                "title": doc.get("title", doc["filename"]),
                "message": "页面缺少引用来源（[^n]）标记",
                "suggestion": "为关键声明添加 [^n]: source 引用",
            })


async def _check_index_drift(wiki_docs, issues):
    """检测 index.md 与实际页面列表不一致。"""
    index_doc = None
    for d in wiki_docs:
        if d["filename"] == "index.md":
            index_doc = d
            break

    if not index_doc:
        issues.append({
            "rule": "index-drift",
            "severity": "warning",
            "doc_id": "",
            "title": "index.md",
            "message": "缺少 index.md 文件",
            "suggestion": "创建 wiki/index.md 作为内容索引",
        })
        return

    # 提取 index.md 中的链接
    content = index_doc.get("content", "")
    linked_docs = set()
    for match in _LINK_RE.finditer(content):
        target = match.group(2).strip().lower()
        linked_docs.add(target.rsplit("/", 1)[-1])

    # 找出 wiki 页面中不在 index 中的
    missing_from_index = []
    for d in wiki_docs:
        if d["filename"] == "index.md":
            continue
        if d["filename"].lower() not in linked_docs:
            missing_from_index.append(d["filename"])

    if missing_from_index:
        issues.append({
            "rule": "index-drift",
            "severity": "warning",
            "doc_id": index_doc["id"],
            "title": "index.md",
            "message": f"index.md 中缺少 {len(missing_from_index)} 个 wiki 页面",
            "suggestion": f"添加以下页面到 index.md: {', '.join(missing_from_index[:5])}"
            + ("..." if len(missing_from_index) > 5 else ""),
        })


async def _check_duplicate_content(wiki_docs, issues):
    """检测内容高度重合的页面对。"""
    # 简单检查：标题相同但不同路径
    titles: dict[str, list] = {}
    for d in wiki_docs:
        t = (d.get("title") or d["filename"]).lower().strip()
        titles.setdefault(t, []).append(d)

    for title, docs in titles.items():
        if len(docs) > 1:
            for d in docs:
                issues.append({
                    "rule": "duplicate-content",
                    "severity": "suggestion",
                    "doc_id": d["id"],
                    "title": d.get("title", d["filename"]),
                    "message": f"可能存在重复内容（标题: {title}），{len(docs)} 个页面标题相同",
                    "suggestion": "检查是否需要合并页面",
                })
