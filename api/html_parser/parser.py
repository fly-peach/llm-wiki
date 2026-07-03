"""HTML → Markdown 核心解析器

将 BeautifulSoup 解析后的 HTML 树递归转换为 Markdown 格式。
"""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag

from html_parser.models import Image, ParseResult
from html_parser.sanitizer import sanitize

# 块级标签（前后加换行）
_BLOCK_TAGS = frozenset({
    "p", "div", "section", "article", "main", "aside",
    "header", "footer", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "blockquote", "pre", "table", "figure",
    "figcaption", "dl", "dt", "dd", "hr", "form",
})

# 忽略的标签（保留内容，去标签）
_INLINE_TAGS = frozenset({
    "span", "a", "strong", "b", "em", "i", "u", "s", "del",
    "code", "kbd", "mark", "sub", "sup", "small", "br",
})


class Parser:
    """HTML → Markdown 解析器"""

    def __init__(self, html: str, url: str = ""):
        self._url = url
        self._images: list[Image] = []
        self._forms: list[dict] = []
        self._list_depth = 0  # 嵌套列表深度跟踪

        self.soup = BeautifulSoup(html, "lxml")
        sanitize(self.soup)

    def parse(self) -> ParseResult:
        """执行解析，返回结构化结果。"""
        title = self._extract_title()
        body = self.soup.find("body") or self.soup
        content = self._process_node(body).strip()

        # 压缩多余空行
        content = re.sub(r"\n{3,}", "\n\n", content)

        return ParseResult(
            title=title,
            content=content,
            images=self._images,
            forms=self._forms,
            metadata={"url": self._url} if self._url else {},
        )

    # ── 标题 ──────────────────────────────────────────

    def _extract_title(self) -> str:
        tag = self.soup.find("title")
        if tag:
            return tag.get_text(strip=True)
        h1 = self.soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        return ""

    # ── 节点处理 ──────────────────────────────────────

    def _process_node(self, node) -> str:
        """递归处理节点树，返回 Markdown 字符串。"""
        if isinstance(node, NavigableString):
            return str(node).strip()

        if not isinstance(node, Tag):
            return ""

        name = node.name.lower() if node.name else ""

        # 忽略的标签：不递归子节点
        if name in ("head", "meta", "link", "title", "source"):
            return ""

        # 块级标签
        if name in _BLOCK_TAGS:
            return self._process_block(node)
        # 行内标签
        if name in _INLINE_TAGS:
            return self._process_inline(node)
        # 图片
        if name == "img":
            return self._process_image(node)
        # 水平线
        if name == "hr":
            return "\n\n---\n\n"
        # 其他（递归子节点）
        return self._process_children(node)

    def _process_children(self, node: Tag) -> str:
        """处理所有子节点并拼接。"""
        parts = []
        for child in node.children:
            result = self._process_node(child)
            if result:
                parts.append(result)
        return "".join(parts)

    # ── 块级元素 ──────────────────────────────────────

    def _process_block(self, node: Tag) -> str:
        name = node.name.lower()

        # 标题 h1-h6
        if re.match(r"^h[1-6]$", name):
            level = int(name[1])
            text = self._process_children(node).strip()
            if text:
                return f"\n\n{'#' * level} {text}\n\n"
            return ""

        # 段落
        if name == "p":
            text = self._process_children(node).strip()
            if text:
                return f"\n\n{text}\n\n"
            return ""

        # 无序列表
        if name == "ul":
            items = self._process_list_items(node, "-")
            return f"\n{items}\n"

        # 有序列表
        if name == "ol":
            items = self._process_list_items(node, "1.")
            return f"\n{items}\n"

        # 引用
        if name == "blockquote":
            text = self._process_children(node).strip()
            lines = text.split("\n")
            quoted = "\n".join(f"> {line}" for line in lines if line.strip())
            return f"\n\n{quoted}\n\n"

        # 代码块
        if name == "pre":
            code_tag = node.find("code")
            lang = ""
            if code_tag:
                classes = code_tag.get("class", [])
                for cls in classes:
                    if cls.startswith("language-"):
                        lang = cls[9:]
                        break
                text = code_tag.get_text()
            else:
                text = node.get_text()
            return f"\n\n```{lang}\n{text.strip()}\n```\n\n"

        # 表格
        if name == "table":
            return self._process_table(node)

        # 通用块级（div, section, article 等）
        text = self._process_children(node).strip()
        if text:
            return f"\n\n{text}\n\n"
        return ""

    def _process_list_items(self, node: Tag, prefix: str) -> str:
        """处理列表项。"""
        items = []
        for li in node.find_all("li", recursive=False):
            text = self._process_children(li).strip()
            if text:
                items.append(f"{prefix} {text}")
        return "\n".join(items)

    # ── 行内元素 ──────────────────────────────────────

    def _process_inline(self, node: Tag) -> str:
        name = node.name.lower()
        text = self._process_children(node)

        if name == "a":
            href = node.get("href", "")
            if href and not href.startswith("#"):
                abs_url = urljoin(self._url, href)
                return f"[{text}]({abs_url})"
            return text

        if name in ("strong", "b"):
            return f"**{text}**"
        if name in ("em", "i"):
            return f"*{text}*"
        if name in ("s", "del"):
            return f"~~{text}~~"
        if name == "code":
            return f"`{text}`"
        if name == "mark":
            return f"=={text}=="
        if name == "br":
            return "\n"
        if name == "sub":
            return f"~{text}~"
        if name == "sup":
            return f"^{text}^"

        return text

    # ── 图片 ──────────────────────────────────────────

    def _process_image(self, node: Tag) -> str:
        src = node.get("src", "")
        alt = node.get("alt", "")
        title = node.get("title", "")

        abs_url = urljoin(self._url, src) if src else ""
        self._images.append(Image(src=abs_url, alt=alt, title=title))

        return f"\n\n![{alt}]({abs_url})\n\n"

    # ── 表格 ──────────────────────────────────────────

    def _process_table(self, node: Tag) -> str:
        """HTML 表格 → Markdown 表格（GFM 格式）"""
        rows = node.find_all("tr")
        if not rows:
            return ""

        # 判断表头（第一个 tr 中有 th）
        has_header = bool(rows[0].find("th"))

        lines: list[str] = []
        for i, tr in enumerate(rows):
            cells = tr.find_all(["td", "th"])
            cell_texts = [self._process_children(c).strip().replace("\n", " ") for c in cells]

            if not cell_texts:
                continue

            lines.append("| " + " | ".join(cell_texts) + " |")

            # 表头后加分隔行
            if i == 0 and has_header:
                lines.append("| " + " | ".join("---" for _ in cell_texts) + " |")

        if not lines:
            return ""

        return "\n\n" + "\n".join(lines) + "\n\n"
