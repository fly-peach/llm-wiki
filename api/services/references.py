"""引用解析器

从 wiki 页面的 Markdown 内容中提取跨文档引用关系。
- 脚注引用 `[^1]: paper.pdf` → cites (wiki→raw)
- 内部链接 `[text](other.md)` → links_to (wiki→wiki)
"""

from __future__ import annotations

import re
from typing import Any

# ── 正则 ──────────────────────────────────────────────

# 脚注引用: [^1]: filename, p.3
# 或者: [^n]: some text with file.pdf, page 5
_CITATION_RE = re.compile(
    r"\[\^[^\]]+\]:\s*(.+?)(?:,\s*p[. ]?\d+)?\s*$",
    re.MULTILINE,
)

# 内部 Markdown 链接: [text](path.md)  排除图片 ![]()
_WIKI_LINK_RE = re.compile(
    r"(?<!!)\[([^\]]*)\]\(([^)]+)\)"
)

# 提取引用中的文件名
_FILENAME_RE = re.compile(r"([\w.\-]+\.(?:pdf|md|txt|html?|pptx?|docx?|xlsx?))", re.IGNORECASE)

# 提取页码
_PAGE_RE = re.compile(r"[,，]\s*p[. ]?(\d+)", re.IGNORECASE)


def parse_filename_from_citation(citation_text: str) -> tuple[str | None, int | None]:
    """从脚注文本中提取文件名和页码。

    示例:
      "paper.pdf, p.3" → ("paper.pdf", 3)
      "see chapter 2 in book.pdf" → ("book.pdf", None)
    """
    filename = None
    match = _FILENAME_RE.search(citation_text)
    if match:
        filename = match.group(1)

    page = None
    match = _PAGE_RE.search(citation_text)
    if match:
        page = int(match.group(1))

    return filename, page


def parse_wiki_links(content: str) -> list[tuple[str, str]]:
    """提取所有内部 Markdown 链接。

    返回: [(link_text, link_path), ...]
    排除: 外部链接(http/https), 锚点链接(#), 图片(![])
    """
    links: list[tuple[str, str]] = []
    for match in _WIKI_LINK_RE.finditer(content):
        link_text = match.group(1)
        link_path = match.group(2).strip()

        # 排除外部/锚点链接
        if link_path.startswith(("http://", "https://", "#", "mailto:")):
            continue

        links.append((link_text, link_path))
    return links


def build_lookup_maps(docs: list[dict[str, Any]]) -> tuple[
    dict[str, dict],   # filename (小写) → doc
    dict[str, dict],   # basename 无扩展名 → doc
    dict[str, dict],   # wiki 相对路径 → doc
]:
    """从文档列表构建 3 层查找映射，加速引用解析。"""
    filename_map: dict[str, dict] = {}
    base_map: dict[str, dict] = {}
    wiki_path_map: dict[str, dict] = {}

    for doc in docs:
        fname = doc["filename"].lower()
        filename_map[fname] = doc

        # basename 无扩展名
        stem = fname.rsplit(".", 1)[0] if "." in fname else fname
        base_map[stem] = doc

        # wiki 相对路径
        if doc.get("source_kind") == "wiki":
            rel = doc["relative_path"].lower()
            wiki_path_map[rel] = doc
            # 也添加不带扩展名的版本
            stem_rel = rel.rsplit(".", 1)[0] if "." in rel else rel
            wiki_path_map[stem_rel] = doc

    return filename_map, base_map, wiki_path_map


def extract_references(
    content: str,
    doc_id: str,
    filename_map: dict[str, dict],
    base_map: dict[str, dict],
    wiki_path_map: dict[str, dict],
) -> list[dict]:
    """从一篇 wiki 页面的 Markdown 正文中提取所有引用边。

    返回: [
        {"target_id": "...", "type": "cites", "page": 3},
        {"target_id": "...", "type": "links_to", "page": None},
    ]
    排除自引用（source == target）。
    """
    edges: list[dict] = []

    # ── 1. 脚注引用 (cites) ──────────────────────────
    for match in _CITATION_RE.finditer(content):
        citation_text = match.group(1).strip()
        filename, page = parse_filename_from_citation(citation_text)

        if not filename:
            continue

        target = (
            filename_map.get(filename.lower())
            or base_map.get(filename.rsplit(".", 1)[0].lower())
        )

        if target and target["id"] != doc_id:
            edges.append({
                "target_id": target["id"],
                "type": "cites",
                "page": page,
            })

    # ── 2. 内部链接 (links_to) ────────────────────────
    seen_targets: set[str] = set()
    for _, link_path in parse_wiki_links(content):
        normalized = link_path.lower().lstrip("/").replace("\\", "/")

        target = wiki_path_map.get(normalized)
        if not target:
            # 尝试 base 匹配
            target = base_map.get(normalized.rsplit(".", 1)[0] if "." in normalized else normalized)

        if target and target["id"] != doc_id and target["id"] not in seen_targets:
            seen_targets.add(target["id"])
            edges.append({
                "target_id": target["id"],
                "type": "links_to",
                "page": None,
            })

    return edges
