"""高亮 → Chunk 映射与物化

将 documents.highlights JSON 中的高亮映射到 document_chunks 的各列:
- annotations_text : 物化脚注块（供 FTS5 索引）
- has_highlight    : 标记块是否有高亮（触发部分索引）
- content          : source_content + annotations_text（FTS5 内容源）

当用户增删高亮时，调用方应：
  1. 先获取旧高亮列表
  2. 写入新高亮到 documents.highlights JSON
  3. 调用 _sync_highlight_chunks(doc_id, old_highlights, new_highlights)
     → 计算 affected chunks → 重建 annotations_text → 更新 document_chunks
     → FTS5 触发器自动感知 content 变化

迁移自 llmwiki 的 api/services/highlight_chunks.py。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Iterable

_WS_RE = re.compile(r"\s+")


def _normalize_ws(value: str) -> str:
    return _WS_RE.sub(" ", value).strip()


# ── 数据类型 ────────────────────────────────────────────


@dataclass
class ChunkRecord:
    """chunk 的最小形态，用于高亮→chunk 映射。"""
    id: str
    chunk_index: int
    source_content: str
    page: int | None
    start_char: int | None  # None 仅存在于旧数据，映射时作 0 处理


# ── 高亮→Chunk 映射 ────────────────────────────────────


def chunks_for_highlight(h: dict, chunks: list[ChunkRecord]) -> list[ChunkRecord]:
    """返回高亮 h 触摸到的 chunk 列表。"""
    if h.get("pdfAnchor"):
        return _chunks_for_pdf_highlight(h, chunks)
    if h.get("textAnchor"):
        return _chunks_for_text_highlight(h, chunks)
    if h.get("anchor"):
        return _chunks_by_text_match(h["anchor"].get("textContent"), chunks)
    return []


def _chunks_for_pdf_highlight(h: dict, chunks: list[ChunkRecord]) -> list[ChunkRecord]:
    pdf = h.get("pdfAnchor") or {}
    page = pdf.get("page")
    if page is None:
        return []
    candidates = [c for c in chunks if c.page == page]
    if not candidates:
        return []
    target = _normalize_ws(pdf.get("textContent") or "")
    if target:
        exact = [c for c in candidates if target in _normalize_ws(c.source_content)]
        if exact:
            exact.sort(key=lambda c: len(c.source_content))
            return exact[:1]
    return candidates


def _chunks_for_text_highlight(h: dict, chunks: list[ChunkRecord]) -> list[ChunkRecord]:
    anchor = h.get("textAnchor") or {}
    ts = anchor.get("textStart")
    te = anchor.get("textEnd")
    if ts is None or te is None:
        return _chunks_by_text_match(anchor.get("textContent"), chunks)

    quoted = _normalize_ws(anchor.get("textContent") or "")
    scored: list[tuple[int, ChunkRecord]] = []
    for c in chunks:
        cs = c.start_char or 0
        ce = cs + len(c.source_content)
        overlap = max(0, min(te, ce) - max(ts, cs))
        if overlap <= 0:
            continue
        score = overlap
        if quoted and quoted in _normalize_ws(c.source_content):
            score += 1_000_000
        scored.append((score, c))

    if not scored:
        return _chunks_by_text_match(quoted, chunks)
    scored.sort(key=lambda t: t[0], reverse=True)
    top_score = scored[0][0]
    return [c for s, c in scored if s >= top_score / 2]


def _chunks_by_text_match(text: str | None, chunks: list[ChunkRecord]) -> list[ChunkRecord]:
    target = _normalize_ws(text or "")
    if not target:
        return []
    matches = [c for c in chunks if target in _normalize_ws(c.source_content)]
    matches.sort(key=lambda c: len(c.source_content))
    return matches[:1]


def assign_highlights_to_chunks(
    chunks: list[ChunkRecord],
    highlights: list[dict],
) -> dict[str, list[dict]]:
    """构建 chunk_id → [highlights] 映射。"""
    out: dict[str, list[dict]] = {}
    for h in highlights:
        for c in chunks_for_highlight(h, chunks):
            out.setdefault(c.id, []).append(h)
    return out


def all_affected_chunks(
    chunks: list[ChunkRecord],
    old_highlights: list[dict],
    new_highlights: list[dict],
) -> set[str]:
    """返回被旧或新高亮触摸的所有 chunk id 集合。

    union 捕捉删除：从旧集合移除的高亮也需要刷新对应 chunk。
    """
    old_map = assign_highlights_to_chunks(chunks, old_highlights)
    new_map = assign_highlights_to_chunks(chunks, new_highlights)
    return set(old_map.keys()) | set(new_map.keys())


# ── 物化输出 ────────────────────────────────────────────


def _sorted_for_render(highlights: list[dict]) -> list[dict]:
    return sorted(
        highlights,
        key=lambda h: (h.get("createdAt") or "", h.get("id") or ""),
    )


def _escape_for_quote(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\"", "\\\"")


def build_annotations_text(highlights: list[dict]) -> str | None:
    """生成物化脚注块，格式: [^user-N]: User highlighted "..." — user note: ...

    无高亮时返回 None（写入 NULL）。
    """
    if not highlights:
        return None
    lines: list[str] = []
    for i, h in enumerate(_sorted_for_render(highlights), start=1):
        quoted = _extract_quoted_text(h)
        if not quoted:
            continue
        comment = (h.get("comment") or "").strip()
        line = f'[^user-{i}]: User highlighted "{_escape_for_quote(quoted)}"'
        if comment:
            line += f" — user note: {comment}"
        lines.append(line)
    return "\n".join(lines) if lines else None


def _extract_quoted_text(h: dict) -> str:
    for key in ("pdfAnchor", "textAnchor", "anchor"):
        anchor = h.get(key)
        if isinstance(anchor, dict):
            text = anchor.get("textContent")
            if text:
                return text
    return ""


def build_chunk_content(source_content: str, annotations_text: str | None) -> str:
    """拼接 source + annotations 为物化 content 列。"""
    if not annotations_text:
        return source_content
    return f"{source_content}\n\n{annotations_text}"


def iter_chunks_with_annotations(
    chunks: list[ChunkRecord],
    affected_ids: Iterable[str],
    new_highlights: list[dict],
) -> Iterable[tuple[ChunkRecord, str | None, bool, str]]:
    """对受影响的 chunk，yield (chunk, annotations_text, has_highlight, new_content)。"""
    affected = set(affected_ids)
    if not affected:
        return
    assignments = assign_highlights_to_chunks(chunks, new_highlights)
    for chunk in chunks:
        if chunk.id not in affected:
            continue
        relevant = assignments.get(chunk.id, [])
        annotations_text = build_annotations_text(relevant)
        has_highlight = annotations_text is not None
        new_content = build_chunk_content(chunk.source_content, annotations_text)
        yield chunk, annotations_text, has_highlight, new_content
