"""文本分块器

将 Markdown 文档按语义边界切分为适合搜索/RAG 的块。
策略：段落边界 → 标题追踪 → 超长块句子级拆分。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import NamedTuple

# 分块配置（默认值，可通过 ChunkConfig 覆盖）
CHUNK_SIZE_TOKENS = 512       # 目标块大小（token）
CHUNK_OVERLAP_TOKENS = 128    # 块间重叠（token）
MIN_CHUNK_TOKENS = 32         # 最小块，低于此值合并到上一块
MAX_CHUNK_CHARS = 10000       # 单块最大字符数


class ChunkConfig(NamedTuple):
    """可配置的分块参数"""
    chunk_size_tokens: int = CHUNK_SIZE_TOKENS
    chunk_overlap_tokens: int = CHUNK_OVERLAP_TOKENS
    min_chunk_tokens: int = MIN_CHUNK_TOKENS
    max_chunk_chars: int = MAX_CHUNK_CHARS

    @classmethod
    def from_size(cls, chunk_size: int, overlap: int | None = None) -> "ChunkConfig":
        """根据 chunk_size 快速构造配置，overlap 默认为 chunk_size 的 1/4。"""
        overlap = overlap if overlap is not None else max(32, chunk_size // 4)
        return cls(
            chunk_size_tokens=chunk_size,
            chunk_overlap_tokens=overlap,
            min_chunk_tokens=max(16, chunk_size // 16),
            max_chunk_chars=chunk_size * 20,
        )


@dataclass
class Chunk:
    """文本块"""
    index: int
    content: str
    page: int | None = None
    start_char: int = 0
    token_count: int = 1
    header_breadcrumb: str = ""     # 如 "研究 > ML > 神经网络"


def estimate_tokens(text: str) -> int:
    """快速估算 token 数量（~4 字符 ≈ 1 token）。"""
    return max(1, len(text) // 4)


def chunk_text(
    content: str,
    page: int | None = None,
    offset: int = 0,
    config: ChunkConfig | None = None,
) -> list[Chunk]:
    """将文档文本切分为块列表。

    参数:
        content: 全量 Markdown 文本
        page: 页码（PDF 场景）
        offset: 字符起始偏移
        config: 分块配置（None 则使用默认值）

    返回:
        Chunk 列表，按文档内容顺序排列，所有块 ≤ max_chunk_chars。
    """
    if not content.strip():
        return []

    cfg = config or ChunkConfig()

    # ── 第一步：按段落/标题边界分段 ──────────────────
    raw_segments = _split_by_boundaries(content)

    # ── 第二步：合并小段、拆分大段 ────────────────────
    chunks = _build_chunks(raw_segments, page, offset, cfg)

    # ── 第三步：注入标题面包屑 ────────────────────────
    chunks = _inject_breadcrumbs(chunks)

    # ── 第四步：强制截断超长块（CJK / 代码块兜底）───
    return _enforce_max_chars(chunks, cfg)


def _split_by_boundaries(text: str) -> list[str]:
    """按 Markdown 标题 + 双换行 边界拆分。

    遇到 `#` 标题行时强制分割，确保标题信息不丢失。
    """
    # 先用双换行分割
    segments = re.split(r"\n\n+", text)

    # 再对包含标题的段进一步分割
    result: list[str] = []
    heading_pattern = re.compile(r"^(#{1,6}\s)", re.MULTILINE)

    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue

        # 如果段内包含标题，在标题前分割
        parts = heading_pattern.split(seg)
        if len(parts) > 1:
            # parts[0] 可能是空，parts[1] 是 `# `，parts[2] 是标题后内容...
            current = ""
            for i, part in enumerate(parts):
                if heading_pattern.match(part):
                    if current.strip():
                        result.append(current.strip())
                    current = part
                else:
                    current += part
            if current.strip():
                result.append(current.strip())
        else:
            result.append(seg)

    return result


def _build_chunks(
    segments: list[str],
    page: int | None,
    offset: int,
    cfg: ChunkConfig,
) -> list[Chunk]:
    """将段落合并成大小合适的块。"""
    chunks: list[Chunk] = []
    buffer = ""
    buffer_tokens = 0
    char_pos = offset

    def flush_buffer():
        nonlocal buffer, buffer_tokens
        if buffer.strip():
            chunks.append(Chunk(
                index=len(chunks),
                content=buffer.strip(),
                page=page,
                start_char=char_pos,
                token_count=estimate_tokens(buffer.strip()),
            ))
        buffer = ""
        buffer_tokens = 0

    for seg in segments:
        seg_tokens = estimate_tokens(seg)

        # 超大段 → 句子级拆分
        if seg_tokens > cfg.chunk_size_tokens * 2:
            flush_buffer()
            sub_chunks = _split_long_segment(seg, page, char_pos, len(chunks), cfg)
            chunks.extend(sub_chunks)
            continue

        # 合并后不超限 → 累加
        if buffer_tokens + seg_tokens <= cfg.chunk_size_tokens:
            buffer += "\n\n" + seg if buffer else seg
            buffer_tokens += seg_tokens
        else:
            # 达到目标大小 → 输出当前缓冲
            flush_buffer()
            buffer = seg
            buffer_tokens = seg_tokens

    flush_buffer()

    # 过小的块合并到上一块
    chunks = _merge_small_chunks(chunks, cfg)

    return chunks


def _split_long_segment(
    text: str,
    page: int | None,
    base_offset: int,
    start_index: int,
    cfg: ChunkConfig,
) -> list[Chunk]:
    """对超长段落按句子边界拆分。"""
    sentences = re.split(r"(?<=[。！？.!?])\s*", text)
    chunks: list[Chunk] = []
    buffer = ""
    buffer_tokens = 0

    for sent in sentences:
        sent_tokens = estimate_tokens(sent)
        if buffer_tokens + sent_tokens > cfg.chunk_size_tokens and buffer:
            chunks.append(Chunk(
                index=start_index + len(chunks),
                content=buffer.strip(),
                page=page,
                start_char=base_offset,
                token_count=estimate_tokens(buffer.strip()),
            ))
            # 重叠：保留最后若干 token 的内容
            overlap_chars = cfg.chunk_overlap_tokens * 4
            buffer = buffer[-overlap_chars:] if len(buffer) > overlap_chars else ""
            buffer_tokens = estimate_tokens(buffer)
        buffer += sent
        buffer_tokens += sent_tokens

    if buffer.strip():
        chunks.append(Chunk(
            index=start_index + len(chunks),
            content=buffer.strip(),
            page=page,
            start_char=base_offset,
            token_count=estimate_tokens(buffer.strip()),
        ))

    return chunks


def _merge_small_chunks(chunks: list[Chunk], cfg: ChunkConfig) -> list[Chunk]:
    """将 token 数过低的块合并到前一相邻块。"""
    if len(chunks) <= 1:
        return chunks

    result: list[Chunk] = []
    for ch in chunks:
        if ch.token_count < cfg.min_chunk_tokens and result:
            # 合并到上一块
            prev = result[-1]
            prev.content += "\n\n" + ch.content
            prev.token_count = estimate_tokens(prev.content)
        else:
            result.append(ch)
    return result


# ── 超长块兜底处理 ─────────────────────────────────────

_SENTENCE_RE = re.compile(r'(?<=[.!?。！？])\s+')


def _enforce_max_chars(chunks: list[Chunk], cfg: ChunkConfig) -> list[Chunk]:
    """对超出 max_chunk_chars 的块按句子边界二次拆分。

    段落级分块对英文 wiki 文本工作良好，但 CJK 密集段落和长代码块
    可能超过 DB 约束。此函数对违规块先按句子拆分，失败时
    硬截断。拆分后的 piece 有独立的 start_char 偏移量，确保下游
    textAnchor 高亮映射能正确计算 end = start_char + len(content)。
    """
    max_chars = cfg.max_chunk_chars
    if not any(len(c.content) > max_chars for c in chunks):
        return chunks

    result: list[Chunk] = []
    for c in chunks:
        if len(c.content) <= max_chars:
            result.append(Chunk(
                index=len(result), content=c.content, page=c.page,
                start_char=c.start_char, token_count=c.token_count,
                header_breadcrumb=c.header_breadcrumb,
            ))
            continue

        base = c.start_char or 0
        offset = 0
        for piece in _split_oversized(c.content, max_chars):
            result.append(Chunk(
                index=len(result), content=piece, page=c.page,
                start_char=base + offset, token_count=estimate_tokens(piece),
                header_breadcrumb=c.header_breadcrumb,
            ))
            offset += len(piece)
    return result


def _split_oversized(text: str, max_chars: int) -> list[str]:
    """按句子边界拆超长文本；无句号可用时硬截断。"""
    parts = _SENTENCE_RE.split(text)
    pieces: list[str] = []
    current = ""
    for part in parts:
        candidate = (current + " " + part).strip() if current else part
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                pieces.append(current)
            if len(part) <= max_chars:
                current = part
            else:
                # 句子拆分失败 → 固定大小硬截断
                for i in range(0, len(part), max_chars):
                    pieces.append(part[i:i + max_chars])
                current = ""
    if current:
        pieces.append(current)
    return pieces


def _inject_breadcrumbs(chunks: list[Chunk]) -> list[Chunk]:
    """为每个块注入标题面包屑，标识其在文档中的位置。

    扫描内容中的 `#` 标题，构建层级路径。
    """
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    breadcrumb_stack: list[str] = []

    for ch in chunks:
        # 从块内容中提取标题
        headings = heading_pattern.findall(ch.content)

        for hashes, title in headings:
            level = len(hashes)
            # 调整面包屑栈
            if len(breadcrumb_stack) >= level:
                breadcrumb_stack = breadcrumb_stack[:level - 1]
            breadcrumb_stack.append(title.strip())

        if breadcrumb_stack:
            ch.header_breadcrumb = " > ".join(breadcrumb_stack)

    return chunks
