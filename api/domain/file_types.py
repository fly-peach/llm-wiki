"""文件类型分类常量

用于判断文件是否需要后端提取、是否属于富文本格式等。
"""

from __future__ import annotations

# ── 纯文本：可直接读取内容并分块 ─────────────────────
SIMPLE_TEXT: frozenset[str] = frozenset({
    "md", "txt", "csv", "json", "xml", "yaml", "yml",
    "toml", "ini", "cfg", "rst", "tex", "latex",
    "py", "js", "ts", "tsx", "jsx", "css", "scss", "html", "htm",
    "sh", "bash", "zsh", "ps1", "bat", "cmd",
    "sql", "graphql", "proto",
})

# ── 需后端提取处理 ──────────────────────────────────
PDF: frozenset[str] = frozenset({"pdf"})
OFFICE: frozenset[str] = frozenset({"pptx", "ppt", "docx", "doc"})
SHEET: frozenset[str] = frozenset({"xlsx", "xls"})
IMAGE: frozenset[str] = frozenset({"png", "jpg", "jpeg", "webp", "gif", "svg", "ico"})
HTML_FILES: frozenset[str] = frozenset({"html", "htm"})

# 需要异步提取处理的文件类型合集
EXTRACTION: frozenset[str] = PDF | OFFICE | SHEET | HTML_FILES

# 所有已知文件类型
ALL_KNOWN: frozenset[str] = SIMPLE_TEXT | EXTRACTION | IMAGE


def is_simple_text(extension: str) -> bool:
    """判断文件扩展名是否为纯文本类型。"""
    return extension.lower().lstrip(".") in SIMPLE_TEXT


def needs_extraction(extension: str) -> bool:
    """判断文件是否需要异步提取处理（PDF/Office/HTML）。"""
    return extension.lower().lstrip(".") in EXTRACTION


def infer_source_kind(relative_path: str) -> str:
    """根据相对路径推断 source_kind。

    规则：
      - 以 'wiki/' 开头 → 'wiki'
      - 以 '.llmwiki/' 开头 → 忽略
      - 其他 → 'raw'（工作区根目录下的文档即原始资料）
    """
    normalized = relative_path.replace("\\", "/").lstrip("/")
    if normalized.startswith("wiki/"):
        return "wiki"
    return "raw"
