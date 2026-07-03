"""HTML 清洗器 — 去除非内容元素（脚本、样式、导航等）"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

# 要去除的标签
_REMOVE_TAGS = frozenset({
    "script", "style", "noscript", "svg", "iframe",
    "canvas", "video", "audio", "object", "embed",
})

# 要去除的 class/id 关键词（nav, footer, sidebar, ad, banner 等）
_NOISE_PATTERNS = frozenset({
    "sidebar", "side-bar", "nav", "navigation", "navbar",
    "footer", "header", "banner", "ad", "ads", "advertisement",
    "cookie", "cookies", "popup", "modal", "overlay",
    "comment", "comments", "social", "share", "related",
    "recommend", "widget", "menu", "breadcrumb",
})

# 要去除的 role 属性值
_NOISE_ROLES = frozenset({
    "navigation", "banner", "complementary", "contentinfo",
    "search", "menu", "menubar",
})


def sanitize(soup: BeautifulSoup) -> None:
    """原地清洗 HTML：移除噪声标签、导航、广告等。

    修改传入的 BeautifulSoup 对象，不返回值。
    """
    # 1. 移除整个标签
    for tag_name in _REMOVE_TAGS:
        for element in soup.find_all(tag_name):
            element.decompose()

    # 2. 移除隐藏元素
    for el in soup.find_all(style=True):
        style_val = str(el.get("style", "")).lower()
        if "display:none" in style_val.replace(" ", "") or \
           "display: none" in style_val:
            el.decompose()

    for el in soup.find_all(attrs={"aria-hidden": "true"}):
        el.decompose()

    # 3. 移除 class/id 带噪声关键词的元素
    for el in soup.find_all(True):  # True = 所有标签
        if not isinstance(el, Tag):
            continue
        el_class = " ".join(el.get("class", [])).lower()
        el_id = str(el.get("id", "")).lower()
        el_role = str(el.get("role", "")).lower()

        # 检查 class/id
        if any(pattern in el_class for pattern in _NOISE_PATTERNS):
            el.decompose()
            continue
        if any(pattern in el_id for pattern in _NOISE_PATTERNS):
            el.decompose()
            continue
        if el_role in _NOISE_ROLES:
            el.decompose()
            continue

    # 4. 移除空标签（递归：从叶子向上）
    for el in soup.find_all(True):
        if not isinstance(el, Tag):
            continue
        # 如果标签只有空白内容且无属性 → 移除
        if _is_empty_tag(el):
            el.decompose()


def _is_empty_tag(tag: Tag) -> bool:
    """判断标签是否为空（无文本内容且无意义子元素）。"""
    # 不处理 self-closing tags (img, br, hr, input 等)
    if tag.name in ("img", "br", "hr", "input", "meta", "link"):
        return False
    # 检查是否有实质内容
    text = tag.get_text(strip=True)
    if text:
        return False
    # 检查是否有有意义的子元素
    for child in tag.children:
        if isinstance(child, Tag):
            if child.name not in _REMOVE_TAGS:
                return False
    return True
