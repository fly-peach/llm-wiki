# LLM Wiki — Python API

## 环境配置

```bash
conda env create -f environment.yml
conda activate llmwiki
cd api && pip install -r requirements.txt
```

## 启动

```bash
cd api
uvicorn main:app --reload --port 8000
```

### 配置文件

复制 `.env.example` 为 `.env` 并按需修改：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| WORKSPACE_PATH | `.` | 工作区根目录（启动时自动打开） |
| PDF_BACKEND | `opendataloader` | PDF 提取后端：`opendataloader` 或 `mistral` |
| MISTRAL_API_KEY | — | Mistral OCR 的 API Key |
| VOYAGE_API_KEY | — | VoyageAI Embedding API Key |
| EMBEDDING_MODEL | `voyage-4-lite` | Embedding 模型 |
| STAGE | `dev` | 运行环境：`dev`/`prod` |
| APP_URL | `http://localhost:3000` | 前端地址 |
| API_URL | `http://localhost:8000` | API 地址 |

## 项目结构

```
api/
├── main.py              # FastAPI 应用入口，管理 lifespan
├── config.py             # 全局配置（Pydantic Settings）
├── deps.py               # FastAPI 依赖注入
├── domain/               # 领域层（业务无关）
│   ├── file_types.py     # 文件类型分类常量
│   ├── processor.py      # 文档处理器（PDF/Office/HTML）
│   └── watcher.py        # 文件系统监控
├── html_parser/          # HTML→Markdown 解析
│   ├── models.py          # 解析结果数据类
│   ├── parser.py          # 核心解析器（BeautifulSoup）
│   ├── sanitizer.py       # HTML 清洗/消毒
│   └── forms.py           # 表单提取
├── infra/                # 基础设施
│   ├── db/sqlite.py       # SQLite 仓库实现
│   ├── workspace/
│   │   ├── init.py         # 工作区初始化
│   │   ├── manager.py      # 工作区生命周期管理
│   │   └── registry.py     # 工作区注册表
│   └── storage/local.py    # 本地文件存储
├── routes/               # HTTP 路由
│   ├── documents.py       # 文档 CRUD + 高亮
│   ├── files.py           # 文件服务（含 Range 支持）
│   ├── graph.py           # 知识图谱查询
│   ├── health.py          # 健康检查
│   ├── ingest.py          # 摄入 API
│   ├── knowledge_bases.py # 知识库管理
│   ├── lint.py            # Lint 健康检查
│   ├── me.py              # 用户信息
│   ├── reindex.py         # 重建索引
│   ├── search.py          # 全文搜索
│   ├── upload.py          # 文件上传
│   └── workspaces.py      # 工作区管理
├── services/             # 业务服务层
│   ├── base.py            # 服务抽象（ABC）
│   ├── local.py           # 本地模式实现
│   ├── chunker.py         # 文本分块器
│   ├── graph.py           # 图算法
│   ├── lint.py            # Lint 规则引擎
│   ├── parsers.py         # Frontmatter 解析
│   ├── pdf_extract.py     # PDF 文本提取
│   ├── references.py      # 引用关系提取
│   ├── types.py           # 请求/响应 Pydantic 模型
│   ├── webclip_assets.py  # 网页剪藏素材处理
│   └── highlight_chunks.py # 高亮→分块映射
└── requirements.txt
```
