# LLM Wiki

> 基于 Andrej Karpathy 的 LLM Wiki 方法论构建的个人知识管理系统。
>
> **Obsidian 是 IDE,LLM 是程序员,wiki 是代码库。**

LLM Wiki 把"原始资料 → 结构化知识"的提炼过程变成可被 AI Agent 自动化的工作流:资料放入 `raw/`,Agent 读取并编译成 `wiki/` 下的结构化页面,用脚注引用和交叉链接构建知识图谱,再通过 MCP 工具集查询与演进。

## 特性

- **三层架构** — Raw / Wiki / Schema 分层,LLM 只读原始资料、只写 wiki
- **知识图谱** — 自动解析 `[^n]` 脚注引用与 `[text](page.md)` 交叉链接,构建可可视化引用网络
- **全文搜索** — SQLite FTS5,按语义分块(512 token)索引,带标题面包屑
- **文件监控** — `raw/` `wiki/` 实时索引,防回环写入
- **MCP 集成** — 17 个 tool 经 fastapi-mcp 挂载于 `/mcp`,复用 REST 接口,ASGI 同进程直连
- **多工作区** — 一个文件夹 = 一个工作区,各自独立的 SQLite 索引
- **实体模板** — 7 种实体(person/paper/concept/event/organization/project/comparison)自动生成 frontmatter
- **Web 控制台** — 文档管理、图谱可视化(D3)、搜索、Schema 编辑

## 三层架构

| 层 | 目录 | 职责 |
|----|------|------|
| Raw | `raw/` | 原始资料(LLM 只读) |
| Wiki | `wiki/` | LLM 生成的结构化知识 |
| Schema | `SCHEMA.md` | 目录结构、命名约定、工作流程规范 |

工作区初始化时自动生成 `wiki/index.md`(内容索引)、`wiki/log.md`(操作日志)、`wiki/overview.md`(总览),由 Agent 维护。

## 快速开始

```bash
# 1. 安装依赖(Python 3.12)
pip install -r api/requirements.txt

# 2. 启动后端(同时提供 REST API + MCP)
python llmwiki.py
#   API:     http://localhost:8000
#   Swagger: http://localhost:8000/docs
#   MCP:     http://localhost:8000/mcp

# 3. (可选)启动前端
cd web && npm install && npm run dev
#   前端: http://localhost:3000 (自动代理 /v1 → :8000)
```

**第一次使用** — 启动后先创建工作区(一个磁盘文件夹),系统会自动建 `raw/` `wiki/` `.llmwiki/index.db` 及种子页面:

```bash
curl -X POST http://localhost:8000/v1/workspaces \
  -H "Content-Type: application/json" \
  -d '{"path":"E:/my-wiki"}'
```

或在 Web 控制台 http://localhost:8000/workspaces 创建。> 工作区路径别选项目根目录,否则会把 `.git`、`node_modules` 等都索引进去。

**生产模式**(前端构建后同进程提供):

```bash
python build_console.py    # 构建前端 → api/static/
python llmwiki.py --prod   # 直接访问 :8000
```

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.12 · FastAPI · SQLite (aiosqlite) · watchfiles |
| 前端 | React 18 · TypeScript · Ant Design 5 · D3 7 · Vite |
| MCP | fastapi-mcp 0.4.0(HTTP Streamable,17 tool) |
| 搜索 | SQLite FTS5(porter + unicode61) |
| 解析 | BeautifulSoup + lxml(HTML→Markdown)、PyMuPDF(PDF,可选) |

## 项目结构

```
llm-wiki/
├── api/              # FastAPI 后端
│   ├── routes/       #   REST 路由(工作区/文档/搜索/图谱/Schema/Lint...)
│   ├── services/     #   业务逻辑(分块/引用/图谱/Lint/Schema)
│   ├── domain/       #   文档处理器 + 文件监控
│   ├── infra/        #   SQLite 仓储 + 工作区注册表
│   ├── html_parser/  #   HTML → Markdown
│   └── main.py       #   应用入口(fastapi-mcp 挂载于 /mcp)
├── shared/           # SQLite schema (sqlite_schema.sql)
├── web/              # React 前端
├── extension/        # Chrome 扩展(WXT,待实现)
├── tests/            # 测试(待补充)
├── llmwiki.py        # 启动 CLI
└── build_console.py  # 前端构建脚本
```

## MCP 集成

MCP server 通过 [fastapi-mcp](https://github.com/tadata-org/fastapi_mcp) 挂载到 FastAPI,**复用 REST 路由**作为 tool,ASGI 进程内直连(无 HTTP 回环、无独立进程)。17 个 tool:

| Tool | 说明 |
|------|------|
| `guide` | 使用指南(新手第一步) |
| `list_workspaces` / `create_workspace` | 工作区管理 |
| `list_documents` / `get_document` / `read_document` | 文档读取 |
| `create_note` / `update_document_content` / `update_document_metadata` / `delete_document` | 文档写入 |
| `get_highlights` / `upsert_highlight` / `delete_highlight` | 高亮标注 |
| `search_documents` | FTS5 全文搜索 |
| `get_graph` / `rebuild_graph` | 知识图谱 |
| `run_lint` | 健康检查 |

**接入 Claude Code**:

```bash
claude mcp add --transport http llmwiki http://localhost:8000/mcp
```

或在 `.mcp.json` / `~/.claude.json` 配置:

```json
{ "mcpServers": { "llmwiki": { "url": "http://localhost:8000/mcp" } } }
```

## API 概览

主要 REST 端点(完整文档见 `/docs`):

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/workspaces` | 创建工作区 |
| GET | `/v1/documents` | 列出文档 |
| POST | `/v1/documents/note` | 创建 wiki 笔记 |
| GET | `/v1/search` | 全文搜索 |
| GET | `/v1/graph` | 知识图谱数据 |
| POST | `/v1/lint` | 健康检查 |
| GET | `/v1/schema` | SCHEMA.md 读写 |
| GET | `/v1/files/{path}` | 工作区文件访问 |

## 五步工作流

1. **Ingest** — 资料放入 `raw/`,或 `create_note` 直接写 wiki
2. **Compile** — 读 raw → 提炼 → 创建/更新 wiki 页面
3. **Link** — `[^n]` 标注引用来源,`[text](page.md)` 交叉链接
4. **Query** — `search_documents` + `read_document` 查找知识
5. **Evolve** — 更新旧页面、修复矛盾、追加新发现

## 开发

```bash
ruff check api/          # 代码风格(配置见 ruff.toml)
pytest tests/            # 测试(待补充)
```
