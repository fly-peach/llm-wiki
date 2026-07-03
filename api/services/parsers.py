"""Frontmatter 解析器

解析 Markdown 文件开头的 YAML frontmatter。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

# frontmatter 正则：匹配开头的 --- ... --- 块
_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL
)


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """解析 Markdown 文本的 YAML frontmatter。

    参数:
        text: 完整的 Markdown 文本

    返回:
        (metadata_dict, content_without_frontmatter)
        如果没有 frontmatter，返回 ({}, 原文)
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    yaml_text = match.group(1)
    try:
        metadata = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError:
        metadata = {}

    content = text[match.end():]
    return metadata, content


def extract_title(
    metadata: dict[str, Any],
    content: str,
    filename: str = "",
) -> str:
    """从元数据、内容或文件名中提取标题。

    优先级: frontmatter.title > 第一个 # 标题 > 文件名
    """
    # frontmatter title
    title = metadata.get("title", "")
    if title:
        return str(title)

    # 第一个 H1
    h1_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if h1_match:
        return h1_match.group(1).strip()

    # 文件名
    if filename:
        return Path(filename).stem.replace("-", " ").replace("_", " ")

    return ""
