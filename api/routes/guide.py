"""使用指南 API

- GET /v1/guide  返回 LLM Wiki 使用指南文本

此端点同时被 fastapi-mcp 暴露为 `guide` tool（新手第一步）。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/v1", tags=["guide"])

GUIDE_TEXT = """# LLM Wiki 使用指南

## 核心理念
Obsidian 是 IDE，LLM 是程序员，wiki 是代码库。

## 五步流程
1. Ingest（摄入）: 资料放入工作区目录，或 create_note 直接写 wiki
2. Compile（编译）: 读工作区中的原始资料 → 写 wiki/ 摘要/实体/总结
3. Link（关联）: 用 [^n]: 标注引用，用 [text](page.md) 交叉链接
4. Query（查询）: search_documents + read_document 查找知识
5. Evolve（进化）: update 旧页面、修复矛盾、追加新发现

## 关键文件（你作为 Agent 负责维护）
- wiki/index.md — 按分类列出全部页面的索引
- wiki/log.md  — 操作日志，每次操作后追加一行

## 写页面规范
- 每实体/概念独立成页
- YAML frontmatter 声明 title 和 tags
- [^n]: 标注引用来源
- Markdown 链接建立页面间引用
"""


@router.get(
    "/guide",
    operation_id="guide",
    summary="获取 LLM Wiki 使用指南，新手第一步应调用此 tool",
)
async def get_guide() -> dict:
    """获取 LLM Wiki 使用指南，新手第一步应该调用此 tool。

    返回五步工作流程（Ingest → Compile → Link → Query → Evolve）与写页面规范。
    """
    return {"guide": GUIDE_TEXT}
