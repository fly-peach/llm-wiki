"""Schema 管理服务

提供实体模板定义、SCHEMA.md 读写、index.md/log.md 维护工具。
"""

from __future__ import annotations

# ── 实体类型定义 ─────────────────────────────────────

ENTITY_TYPES: dict[str, dict] = {
    "person": {
        "label": "人物",
        "folder": "entities/person",
        "frontmatter": {
            "type": "person",
            "title": "",
            "tags": [],
            "organization": "",
            "field": "",
            "works": [],
            "sources": [],
        },
        "sections": [
            "## 简介",
            "## 研究方向",
            "## 代表作品",
            "## 资料来源",
        ],
    },
    "paper": {
        "label": "论文摘要",
        "folder": "entities/paper",
        "frontmatter": {
            "type": "paper",
            "title": "",
            "tags": [],
            "source": "",
            "authors": [],
            "year": "",
        },
        "sections": [
            "## 核心贡献",
            "## 方法",
            "## 局限",
            "## 前置工作",
        ],
    },
    "concept": {
        "label": "概念",
        "folder": "entities/concept",
        "frontmatter": {
            "type": "concept",
            "title": "",
            "tags": [],
            "domain": "",
        },
        "sections": [
            "## 定义",
            "## 关键公式",
            "## 关联概念",
            "## 知识库演进",
        ],
    },
    "event": {
        "label": "事件",
        "folder": "entities/event",
        "frontmatter": {
            "type": "event",
            "title": "",
            "tags": [],
            "date": "",
            "location": "",
        },
        "sections": [
            "## 时间线",
            "## 参与方",
            "## 影响",
        ],
    },
    "organization": {
        "label": "组织",
        "folder": "entities/organization",
        "frontmatter": {
            "type": "organization",
            "title": "",
            "tags": [],
            "industry": "",
            "scale": "",
        },
        "sections": [
            "## 概况",
            "## 核心产品",
            "## 相关人物",
        ],
    },
    "project": {
        "label": "项目",
        "folder": "entities/project",
        "frontmatter": {
            "type": "project",
            "title": "",
            "tags": [],
            "tech_stack": [],
            "status": "",
        },
        "sections": [
            "## 概述",
            "## 技术栈",
            "## 相关论文",
        ],
    },
    "comparison": {
        "label": "对比分析",
        "folder": "comparisons",
        "frontmatter": {
            "type": "comparison",
            "title": "",
            "tags": [],
            "dimensions": [],
        },
        "sections": [
            "## 对比维度",
            "| 维度 | A | B |",
            "|------|---|---|",
            "## 结论",
            "## 数据来源",
        ],
    },
}

# SCHEMA.md 默认模板
DEFAULT_SCHEMA = """# SCHEMA.md — Wiki 结构规范

> 此文件定义 wiki 的目录结构、命名约定和工作流程。
> LLM 在每次操作时必须遵守此规范。

## 目录结构

```
wiki/
├── index.md          # 内容索引（每次操作必须更新）
├── log.md            # 操作日志（每次操作必须追加一行）
├── overview.md       # 知识库总览
├── entities/         # 实体页面
│   ├── person/       # 人物
│   ├── paper/        # 论文摘要
│   ├── concept/      # 概念
│   ├── event/        # 事件
│   ├── organization/ # 组织
│   └── project/      # 项目
├── summaries/        # 摘要页面
├── comparisons/      # 对比分析
├── reviews/          # 综述文章
└── topics/           # 主题页面
```

> 原始资料直接放在工作区根目录下，wiki/ 用于 LLM 编译的结构化知识。

## 命名约定

- **文件名**: kebab-case (`andrew-ng.md`, `transformer-architecture.md`)
- **标题**: Plain English (`Andrew Ng`, `Transformer Architecture`)
- **路径格式**: `wiki/{类别}/{文件名}.md`

## 工作流程

1. **Ingest**: 新资料放入工作区目录（根目录或子目录均可）
2. **Compile**: 阅读原始资料 → 提炼关键信息 → 创建/更新 wiki 页面
3. **Link**: 用 `[^n]: file.pdf` 标注引用，用 `[text](page.md)` 交叉链接
4. **Query**: 使用搜索工具查找已有知识
5. **Evolve**: 更新旧页面、修复矛盾、追加新发现

## 写页面规范

- 每个实体/概念独立成页
- 使用 YAML frontmatter 声明 title 和 tags
- 每个声明必须有 `[^n]` 引用来源
- 用 Markdown 链接建立页面间引用
- index.md 在每次操作后必须更新
- log.md 在每次操作后必须追加一行

## 实体类型

{entity_types}
"""


def generate_schema_md() -> str:
    """生成 SCHEMA.md 内容（含实体类型描述）。"""
    type_descriptions = []
    for key, info in ENTITY_TYPES.items():
        fields = ", ".join(info["frontmatter"].keys())
        type_descriptions.append(
            f"- **{info['label']}** (`{key}`): 目录 `{info['folder']}/` | 字段: {fields}"
        )

    # 用 replace 而非 str.format，避免模板里的 {类别}/{文件名} 等字面花括号被当成占位符
    return DEFAULT_SCHEMA.replace("{entity_types}", "\n".join(type_descriptions))


def get_template(entity_type: str) -> str:
    """获取指定实体类型的 Markdown 模板。"""
    info = ENTITY_TYPES.get(entity_type)
    if not info:
        return ""

    fm = info["frontmatter"]
    fm_lines = ["---"]
    for key, value in fm.items():
        if isinstance(value, list):
            fm_lines.append(f"{key}: []")
        elif isinstance(value, str) and value:
            fm_lines.append(f"{key}: {value}")
        else:
            fm_lines.append(f"{key}:")
    fm_lines.append("---")

    sections = info["sections"]
    return "\n".join(fm_lines) + "\n\n" + "\n\n".join(sections) + "\n"
