# 工作区 ID 接入优化方案

## 目标
统一工作区 ID 的接入方式：
- **移除** `X-Workspace-ID` header 机制（中间件 + contextvar + MCP headers）
- **MCP**：通过 `set_current_workspace` / `get_current_workspace` tool 切换工作区
- **前端**：workspace ID 进入 URL（`/w/:wsId/...`），可分享、可刷新、有历史记录

最终后端只保留一条工作区解析路径：**全局 current > 第一个有效工作区**。

---

## 一、后端改动

### 1. `api/deps.py` — 移除 header 机制，简化解析
- 删除 `_request_ws_id` ContextVar
- 删除 `set_request_workspace`、`get_request_workspace`
- 简化 `find_valid_workspace`：优先级 = **全局 `_current_ws_id` > 第一个有效工作区**（移除 header 优先级分支）
- 更新 docstring，去掉"请求头 X-Workspace-ID"说明

### 2. `api/main.py`
- 删除 `WorkspaceHeaderMiddleware` 类
- 删除 `app.add_middleware(WorkspaceHeaderMiddleware)`
- 删除 `set_request_workspace` 导入
- MCP `FastApiMCP(...)` 的 `headers=["authorization", "x-workspace-id"]` → 去掉 `"x-workspace-id"`（只保留 `authorization` 或直接移除 headers 参数）
- `MCP_INCLUDE_OPERATIONS` 增加：`"set_current_workspace"`、`"get_current_workspace"`

### 3. `api/routes/workspaces.py` — 优化两个切换端点
- `set_current_workspace`（PUT /v1/workspaces/current）：
  - summary 改为："切换当前工作区（MCP/前端调用，后续操作作用于此工作区）"
  - 返回值增加 `name`、`path`，方便 MCP 切换后立即知道工作区信息
- `get_current_workspace`（GET /v1/workspaces/current）：
  - summary 改为："查询当前工作区 ID（未设置则回退到第一个有效工作区）"

### 4. `api/routes/guide.py` — 更新使用指南
GUIDE_TEXT 增加"多工作区切换"章节：
```
## 多工作区切换
- list_workspaces 查看所有已注册工作区
- set_current_workspace(ws_id) 切换到目标工作区
- 切换后所有 tool（list_documents/search_documents/create_note 等）自动作用在该工作区
- get_current_workspace 可随时查询当前工作区
```

---

## 二、前端改动（URL 化）

### 路由结构
```
/                       → 重定向到 /w/{currentWsId}，无工作区则 Onboarding
/workspaces             → WorkspaceManager（不带 wsId）
/w/:wsId                → Layout 包裹的嵌套路由
  index                 → Dashboard
  documents             → Documents
  documents/:id         → DocumentView
  graph                 → GraphView
  schema                → SchemaEditor
  search                → SearchPage
```

### 1. `web/src/App.tsx` — 嵌套路由
- 改为嵌套结构，`Layout` 作为 `/w/:wsId` 的 element，子路由用相对路径
- `/` 根路径：有 current → `<Navigate to={`/w/${current}`} />`；无 → `<Onboarding />`

### 2. `web/src/lib/workspace-context.tsx` — current 来自 URL
- `current` 改为从 URL 的 `:wsId` 读取（用 `useParams` 或从 location 解析），不再依赖后端 GET /current
- `switchTo(wsId)`：调 `api.setCurrentWorkspace(wsId)` 同步后端全局 current，并 `navigate(`/w/${wsId}`)` 切换 URL
- `refresh`：仍拉 workspaces 列表（用于下拉选择器）

### 3. `web/src/components/Layout.tsx`
- 侧边栏工作区 Select 切换时调 `switchTo`（已会 navigate）
- NAV 链接改相对路径：`to="documents"`、`to="search"` 等（相对当前 `/w/:wsId`）
- 面包屑读 `:wsId` 对应的 workspace name

### 4. 各页面内部链接加 wsId 前缀
统一用 **相对路径**（最干净，React Router v6 嵌套路由下 `to="documents"` 相对当前 `:wsId`）：
- `Documents.tsx:171` — `<Link to={`documents/${d.id}`}>`
- `Dashboard.tsx:114,134` — 文档详情链接
- `Dashboard.tsx:171-173` — 浏览/搜索/图谱按钮
- `DocumentView.tsx:101` — `nav("documents")`（删除后回列表）
- `GraphView.tsx:370` — 节点跳转
- `DocSidebar.tsx:29` — 引用文档跳转
- `SearchPage.tsx:105` — `linkFor(r)` 搜索结果跳转
- `MdRenderer.tsx:37` — wiki 链接跳转（`nav(\`documents/${id}\`)` 或带 query）
- `FileTree.tsx:73` — 目录跳转

> 跨工作区跳转（如 Onboarding 创建后）用绝对路径 `/w/{wsId}`。

### 5. `web/src/components/Onboarding.tsx`
- 创建工作区后 `navigate(`/w/${ws.id}`)` 而非依赖后端 current

### 6. `web/src/pages/WorkspaceManager.tsx` — 移除 header 锁定 UI
- 删除"锁定工作区"选择器（`lockWsId`、`lockWsName` 及相关 state）
- 删除各 `buildXxxHttpSteps` 里的 `X-Workspace-ID` header 注入逻辑
- 改为说明文字："MCP 通过 `set_current_workspace` tool 切换工作区，无需在客户端配置中锁定 header"
- Tool 清单 `MCP_TOOLS` 增加 `set_current_workspace`、`get_current_workspace`，标签数 17 → 19，相关文案同步

---

## 三、已知限制
后端全局 `_current_ws_id` 是进程级状态，**多浏览器标签页同时切换不同工作区会互相影响**。本地单用户场景可接受。若后续需要多标签页独立，可改为每个 API 请求携带 `ws_id` 查询参数（本次不做）。

---

## 四、改动文件清单

**后端（4 个）**：
- `api/deps.py`
- `api/main.py`
- `api/routes/workspaces.py`
- `api/routes/guide.py`

**前端（10 个）**：
- `web/src/App.tsx`
- `web/src/lib/workspace-context.tsx`
- `web/src/components/Layout.tsx`
- `web/src/components/Onboarding.tsx`
- `web/src/pages/WorkspaceManager.tsx`
- `web/src/pages/Documents.tsx`
- `web/src/pages/Dashboard.tsx`
- `web/src/pages/DocumentView.tsx`
- `web/src/pages/GraphView.tsx`
- `web/src/components/DocSidebar.tsx`
- `web/src/pages/SearchPage.tsx`
- `web/src/components/MdRenderer.tsx`
- `web/src/components/FileTree.tsx`

---

## 五、验证
1. **前端**：切换工作区 → URL 变化；刷新页面 → 仍在该工作区；文档详情/搜索结果跳转链接正确
2. **MCP**：`list_workspaces` → `set_current_workspace(ws_id)` → `list_documents` 链路返回目标工作区数据
3. **后端**：无 header 时 `find_valid_workspace` 正确按 current > 第一个回退；`set_current_workspace` 返回 name/path
