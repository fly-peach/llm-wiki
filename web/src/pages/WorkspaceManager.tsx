import { useState, useEffect } from "react";
import { Input, Button, Card, List, Typography, message, Space, Popconfirm, Tag, Tabs, Collapse, Tooltip, Radio } from "antd";
import {
    PlusOutlined,
    DeleteOutlined,
    FolderOpenOutlined,
    CheckCircleOutlined,
    ApiOutlined,
    CopyOutlined,
    LinkOutlined,
    CodeOutlined,
    GlobalOutlined,
    DesktopOutlined,
} from "@ant-design/icons";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace-context";
import { relativeTime } from "../lib/format";

const { Text, Title, Paragraph } = Typography;

// ── 自动推断服务地址 ───────────────────────────── 

function useServerUrl(): { localhost: string; lan: string; mcpPath: string } {
    const origin = window.location.origin;  // 如 http://192.168.1.5:8000
    const mcpPath = "/mcp";
    
    // 如果是 localhost 访问，用 localhost；否则用当前 origin
    const isLocalhost = origin.includes("localhost") || origin.includes("127.0.0.1");
    return {
        localhost: `http://localhost:${window.location.port || "8000"}${mcpPath}`,
        lan: isLocalhost ? "" : `${origin}${mcpPath}`,
        mcpPath,
    };
}

export default function WorkspaceManager() {
    const { workspaces, current, switchTo, refresh, loaded } = useWorkspace();
    const [newPath, setNewPath] = useState("");
    const [newName, setNewName] = useState("");
    const [creating, setCreating] = useState(false);
    const [transportType, setTransportType] = useState<"http" | "command">("http");
    const serverUrl = useServerUrl();
    
    // MCP 端点地址（如果是局域网访问就用局域网地址，否则用 localhost）
    const mcpHttpUrl = serverUrl.lan || serverUrl.localhost;

    const handleCreate = async () => {
        if (!newPath.trim()) {
            message.warning("请填写工作区路径");
            return;
        }
        setCreating(true);
        try {
            const ws = await api.createWorkspace(newPath.trim(), newName.trim() || undefined);
            message.success(`工作区 "${ws.name}" 创建成功`);
            await refresh();
            await switchTo(ws.id);
            setNewPath("");
            setNewName("");
        } catch (e: any) {
            message.error(e.message || "创建失败");
        } finally {
            setCreating(false);
        }
    };

    const handleDelete = async (id: string) => {
        await api.deleteWorkspace(id);
        message.success("已注销(磁盘文件未删除)");
        await refresh();
    };

    return (
        <div style={{ maxWidth: 900 }}>
            <h1 className="page-title">工作区管理</h1>

            <Card title="创建工作区" size="small" style={{ marginBottom: 16 }}>
                <Space direction="vertical" style={{ width: "100%" }}>
                    <Input
                        addonBefore="路径"
                        placeholder="E:/my-wiki"
                        value={newPath}
                        onChange={(e) => setNewPath(e.target.value)}
                    />
                    <Input
                        addonBefore="名称"
                        placeholder="(可选) 默认用文件夹名"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                    />
                    <Space>
                        <Button type="primary" icon={<PlusOutlined />} loading={creating} onClick={handleCreate}>
                            创建
                        </Button>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                            ⚠️ 路径别选项目根目录，否则会把 .git/node_modules 等都索引进去
                        </Text>
                    </Space>
                </Space>
            </Card>

            <Card title={`已注册工作区 (${workspaces.length})`} size="small">
                {loaded && workspaces.length === 0 ? (
                    <Text type="secondary">暂无工作区，创建一个开始使用</Text>
                ) : (
                    <List
                        dataSource={workspaces}
                        renderItem={(w) => {
                            const isCurrent = w.id === current;
                            return (
                                <List.Item>
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
                                        <div>
                                            <Space>
                                                <FolderOpenOutlined />
                                                <Text strong>{w.name}</Text>
                                                {isCurrent && (
                                                    <Tag color="green" icon={<CheckCircleOutlined />} style={{ border: "none" }}>
                                                        当前
                                                    </Tag>
                                                )}
                                            </Space>
                                            <br />
                                            <Text type="secondary" style={{ fontSize: 12, fontFamily: "monospace" }}>{w.path}</Text>
                                            <br />
                                            <Text type="secondary" style={{ fontSize: 11 }}>
                                                kind: {w.kind} · 创建 {relativeTime(w.created_at)}
                                            </Text>
                                        </div>
                                        <Space>
                                            {!isCurrent && (
                                                <Button size="small" onClick={() => switchTo(w.id)}>
                                                    设为当前
                                                </Button>
                                            )}
                                            <Popconfirm
                                                title="确定注销?"
                                                description="仅从注册表移除，不删除磁盘文件"
                                                onConfirm={() => handleDelete(w.id)}
                                            >
                                                <Button danger icon={<DeleteOutlined />} size="small">注销</Button>
                                            </Popconfirm>
                                        </Space>
                                    </div>
                                </List.Item>
                            );
                        }}
                    />
                )}
            </Card>

            {/* ── MCP 配置 ─────────────────────────────────── */}
            <Card
                title={
                    <Space>
                        <ApiOutlined />
                        <span>MCP 配置</span>
                        <Tag color="blue">17 个 Tool</Tag>
                    </Space>
                }
                size="small"
                style={{ marginTop: 16 }}
            >
                <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                    LLM Wiki 通过 <Text code>fastapi-mcp</Text> 将 REST 接口暴露为 MCP Tool，
                    同进程 ASGI 直连，无需额外启动进程。
                </Paragraph>

                {/* 传输格式选择 */}
                <Space style={{ marginBottom: 12 }}>
                    <Text strong>传输格式：</Text>
                    <Radio.Group
                        value={transportType}
                        onChange={(e) => setTransportType(e.target.value)}
                        optionType="button"
                        size="small"
                    >
                        <Tooltip title="HTTP 客户端直接连接 MCP 端点（推荐，本服务使用此模式）">
                            <Radio.Button value="http">
                                <LinkOutlined /> HTTP (Streamable)
                            </Radio.Button>
                        </Tooltip>
                        <Tooltip title="STDIO 模式：由客户端启动本地进程（MCP 标准格式，本服务不适用，仅供参考）">
                            <Radio.Button value="command">
                                <DesktopOutlined /> command (STDIO)
                            </Radio.Button>
                        </Tooltip>
                    </Radio.Group>
                </Space>

                {/* MCP 端点信息 - 自动识别 */}
                <Card
                    size="small"
                    style={{
                        marginBottom: 16,
                        background: "var(--llm-indigo-light)",
                        border: "1px solid var(--llm-indigo)",
                    }}
                >
                    <Space direction="vertical" style={{ width: "100%" }}>
                        <Space style={{ width: "100%", justifyContent: "space-between" }}>
                            <Space>
                                <LinkOutlined style={{ color: "var(--llm-indigo)" }} />
                                <Text strong style={{ fontSize: 14, fontFamily: "monospace" }}>
                                    {mcpHttpUrl}
                                </Text>
                                <Text copyable={{ text: mcpHttpUrl }} />
                            </Space>
                            <Tooltip title="复制 MCP 端点地址">
                                <Button
                                    size="small"
                                    icon={<CopyOutlined />}
                                    onClick={() => {
                                        navigator.clipboard.writeText(mcpHttpUrl);
                                        message.success("已复制 MCP 端点地址");
                                    }}
                                >
                                    复制
                                </Button>
                            </Tooltip>
                        </Space>
                        {serverUrl.lan && (
                            <Tag color="green" icon={<GlobalOutlined />}>
                                当前通过局域网访问，配置自动使用 {mcpHttpUrl}
                            </Tag>
                        )}
                        {!serverUrl.lan && (
                            <Text type="secondary" style={{ fontSize: 11 }}>
                                💡 如从其他设备访问，请将 localhost 替换为服务器局域网 IP
                            </Text>
                        )}
                    </Space>
                </Card>

                {/* 接入教程 Tabs */}
                <Tabs
                    defaultActiveKey="claude"
                    items={[
                        {
                            key: "claude",
                            label: "Claude Desktop",
                            children: (
                                <MCPGuideBlock
                                    title="Claude Desktop 接入"
                                    transport={transportType}
                                    mcpUrl={mcpHttpUrl}
                                    steps={transportType === "http" ? buildClaudeHttpSteps(mcpHttpUrl) : CLAUDE_STDIO_STEPS}
                                />
                            ),
                        },
                        {
                            key: "vscode",
                            label: "VS Code / Copilot",
                            children: (
                                <MCPGuideBlock
                                    title="VS Code Copilot 接入"
                                    transport={transportType}
                                    mcpUrl={mcpHttpUrl}
                                    steps={transportType === "http" ? buildVscodeHttpSteps(mcpHttpUrl) : VSCODE_STDIO_STEPS}
                                />
                            ),
                        },
                        {
                            key: "cursor",
                            label: "Cursor",
                            children: (
                                <MCPGuideBlock
                                    title="Cursor 接入"
                                    transport={transportType}
                                    mcpUrl={mcpHttpUrl}
                                    steps={buildCursorSteps(mcpHttpUrl)}
                                />
                            ),
                        },
                        {
                            key: "generic",
                            label: "通用 / 其他客户端",
                            children: (
                                <MCPGuideBlock
                                    title="通用 MCP 客户端接入"
                                    transport={transportType}
                                    mcpUrl={mcpHttpUrl}
                                    steps={buildGenericSteps(mcpHttpUrl)}
                                />
                            ),
                        },
                        {
                            key: "tools",
                            label: (
                                <Space size={4}>
                                    <CodeOutlined />
                                    <span>Tool 清单</span>
                                </Space>
                            ),
                            children: <MCPToolList />,
                        },
                    ]}
                />
            </Card>
        </div>
    );
}

// ── 子组件：MCP 接入指南步骤块（支持 HTTP / STDIO 两种格式）───

interface GuideStep {
    label: string;
    desc: React.ReactNode;
}

function MCPGuideBlock({
    title,
    transport,
    mcpUrl,
    steps,
}: {
    title: string;
    transport: "http" | "command";
    mcpUrl: string;
    steps: GuideStep[];
}) {
    return (
        <div>
            <Title level={5} style={{ marginTop: 0 }}>
                {title}
            </Title>
            <Collapse
                size="small"
                items={steps.map((s, i) => ({
                    key: String(i),
                    label: (
                        <Text strong>
                            {i + 1}. {s.label}
                        </Text>
                    ),
                    children: <div>{s.desc}</div>,
                }))}
            />
        </div>
    );
}

// ── MCP 配置代码块渲染 ─────────────────────────

function MCPJsonBlock({ code }: { code: string }) {
    return (
        <div
            style={{
                background: "#1e1e2e",
                color: "#cdd6f4",
                padding: 12,
                borderRadius: 8,
                fontFamily: "'JetBrains Mono', Consolas, monospace",
                fontSize: 12,
                lineHeight: 1.7,
                overflow: "auto",
            }}
        >
            <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{code}</pre>
        </div>
    );
}

function MCPShellBlock({ code }: { code: string }) {
    return (
        <div
            style={{
                background: "#1e1e2e",
                color: "#cdd6f4",
                padding: 10,
                borderRadius: 8,
                fontFamily: "'JetBrains Mono', Consolas, monospace",
                fontSize: 12,
                marginTop: 6,
            }}
        >
            <code style={{ background: "transparent", color: "#a6e3a1" }}>{code}</code>
        </div>
    );
}

// ── 各客户端 STDIO 模式步骤数据（标准 MCP 格式，仅供参考）────

const CLAUDE_STDIO_STEPS: GuideStep[] = [
    {
        label: "打开配置文件",
        desc: (
            <span>
                Windows: <Text code copyable>%APPDATA%\Claude\claude_desktop_config.json</Text>
                <br />
                macOS: <Text code copyable>~/Library/Application Support/Claude/claude_desktop_config.json</Text>
            </span>
        ),
    },
    {
        label: "添加 MCP Server 配置（command 格式）",
        desc: (
            <div>
                <MCPJsonBlock
                    code={`{\n  "mcpServers": {\n    "example-server": {\n      "command": "npx",\n      "args": ["-y", "@example/mcp-server"],\n      "env": {\n        "API_KEY": "<YOUR_API_KEY>"\n      }\n    }\n  }\n}`}
                />
                <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                    ⚠️ 以上是 MCP 标准的 command/args 格式示例，适用于需要本地启动进程的 MCP Server。
                    LLM Wiki 使用 HTTP 传输模式，不适用此格式。请切换到「HTTP」标签页获取正确配置。
                </Paragraph>
            </div>
        ),
    },
    {
        label: "重启 Claude Desktop",
        desc: "保存配置文件后，完全退出并重新启动 Claude Desktop。",
    },
];

const VSCODE_STDIO_STEPS: GuideStep[] = [
    {
        label: "创建 .mcp.json",
        desc: (
            <span>
                在项目根目录或 <Text code>$HOME</Text> 创建 <Text code>.mcp.json</Text> 文件
            </span>
        ),
    },
    {
        label: "写入配置（command 格式）",
        desc: (
            <div>
                <MCPJsonBlock
                    code={`{\n  "servers": {\n    "example-server": {\n      "command": "npx",\n      "args": ["-y", "@example/mcp-server"],\n      "env": {\n        "API_KEY": "<YOUR_API_KEY>"\n      }\n    }\n  }\n}`}
                />
                <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
                    ⚠️ 以上是 MCP 标准的 command/args 格式示例。LLM Wiki 使用 HTTP 传输模式，
                    请切换到「HTTP」标签页获取正确配置。
                </Paragraph>
            </div>
        ),
    },
    {
        label: "重新加载 VS Code",
        desc: "保存后执行 Cmd/Ctrl+Shift+P → Developer: Reload Window。",
    },
];

// 占位符 — 运行时由 hook 替换为实际 URL

// ── 根据 mcpUrl 动态生成各客户端步骤 ─────────────

function buildClaudeHttpSteps(mcpUrl: string): GuideStep[] {
    return [
        {
            label: "打开配置文件",
            desc: (
                <span>
                    Windows: <Text code copyable>%APPDATA%\Claude\claude_desktop_config.json</Text>
                    <br />
                    macOS: <Text code copyable>~/Library/Application Support/Claude/claude_desktop_config.json</Text>
                </span>
            ),
        },
        {
            label: "添加 MCP Server 配置",
            desc: <MCPJsonBlock code={JSON.stringify({ mcpServers: { llmwiki: { type: "http", url: mcpUrl } } }, null, 2)} />,
        },
        {
            label: "重启 Claude Desktop",
            desc: "保存配置文件后，完全退出并重新启动 Claude Desktop。启动后点击输入框旁的 🔌 图标，应能看到 17 个 LLM Wiki Tool。",
        },
        {
            label: "使用 CLI 快速添加",
            desc: (
                <div>
                    <Text>也可用一行命令：</Text>
                    <MCPShellBlock code={`claude mcp add --transport http llmwiki ${mcpUrl}`} />
                </div>
            ),
        },
    ];
}

function buildVscodeHttpSteps(mcpUrl: string): GuideStep[] {
    return [
        {
            label: "创建 .mcp.json",
            desc: (
                <span>
                    在项目根目录或 <Text code>$HOME</Text> 创建 <Text code>.mcp.json</Text> 文件
                </span>
            ),
        },
        {
            label: "写入配置",
            desc: <MCPJsonBlock code={JSON.stringify({ servers: { llmwiki: { type: "http", url: mcpUrl } } }, null, 2)} />,
        },
        {
            label: "重新加载 VS Code",
            desc: "保存后执行 Cmd/Ctrl+Shift+P → Developer: Reload Window。之后在 Copilot Chat 中即可调用 LLM Wiki 的知识管理工具。",
        },
    ];
}

function buildCursorSteps(mcpUrl: string): GuideStep[] {
    return [
        {
            label: "打开 Cursor Settings",
            desc: "Cmd/Ctrl+Shift+J → MCP 标签页 → Add new MCP server",
        },
        {
            label: "填写配置",
            desc: (
                <div>
                    <Text strong>Name: </Text>
                    <Text code>llmwiki</Text>
                    <br />
                    <Text strong>Type: </Text>
                    <Text code>HTTP</Text>
                    <br />
                    <Text strong>URL: </Text>
                    <Text code copyable>{mcpUrl}</Text>
                </div>
            ),
        },
        {
            label: "验证连接",
            desc: "添加后 Cursor 会自动尝试连接。成功后在 MCP 面板会显示绿色状态灯和 17 个可用 Tool。",
        },
    ];
}

function buildGenericSteps(mcpUrl: string): GuideStep[] {
    return [
        {
            label: "MCP 端点",
            desc: <Text code copyable style={{ fontSize: 14 }}>{mcpUrl}</Text>,
        },
        {
            label: "传输协议",
            desc: (
                <Text>
                    采用 MCP Streamable HTTP 传输（<Text code>fastapi-mcp</Text>），
                    支持标准 MCP 客户端连接。
                </Text>
            ),
        },
        {
            label: "手动验证 (curl)",
            desc: (
                <MCPJsonBlock
                    code={`# 列出所有 Tool\ncurl -X POST ${mcpUrl} \\\\\n  -H "Content-Type: application/json" \\\\\n  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'\n\n# 调用 guide tool\ncurl -X POST ${mcpUrl} \\\\\n  -H "Content-Type: application/json" \\\\\n  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"guide","arguments":{}}}'`}
                />
            ),
        },
    ];
}

// ── 子组件：MCP Tool 清单 ───────────────────────────

interface ToolInfo {
    name: string;
    description: string;
    category: string;
}

const MCP_TOOLS: ToolInfo[] = [
    { name: "guide", description: "获取 LLM Wiki 使用指南（新手第一步应调用此 tool）", category: "指南" },
    { name: "list_workspaces", description: "列出所有已注册的工作区（知识库）", category: "工作区" },
    { name: "create_workspace", description: "创建并初始化新的工作区（知识库）", category: "工作区" },
    { name: "list_documents", description: "列出工作区中的文档，可按 source_kind、status、entity_type 和路径过滤", category: "文档" },
    { name: "get_document", description: "获取单个文档的元数据（不含全文内容）", category: "文档" },
    { name: "read_document", description: "读取文档正文内容", category: "文档" },
    { name: "create_note", description: "在 wiki/ 下创建新的 Markdown 笔记", category: "文档" },
    { name: "update_document_content", description: "更新文档正文内容（需提供版本号，乐观锁）", category: "文档" },
    { name: "update_document_metadata", description: "更新文档元数据（title、tags、entity_type 等）", category: "文档" },
    { name: "delete_document", description: "删除文档（软删除，标记为 deleted 状态）", category: "文档" },
    { name: "get_highlights", description: "获取文档的高亮标注列表", category: "标注" },
    { name: "upsert_highlight", description: "创建或更新文档中的高亮标注", category: "标注" },
    { name: "delete_highlight", description: "删除文档中的高亮标注", category: "标注" },
    { name: "search_documents", description: "FTS5 全文搜索文档分块内容，返回匹配片段及标题面包屑", category: "搜索" },
    { name: "get_graph", description: "获取知识图谱数据（节点 + 引用边 + 统计）", category: "图谱" },
    { name: "rebuild_graph", description: "重建知识图谱（解析所有脚注引用与交叉链接）", category: "图谱" },
    { name: "run_lint", description: "运行健康检查，检测死链接、缺失引用等问题", category: "健康" },
];

const TOOL_CATEGORIES = ["指南", "工作区", "文档", "标注", "搜索", "图谱", "健康"];

function MCPToolList() {
    return (
        <div>
            <Paragraph type="secondary" style={{ marginBottom: 12 }}>
                以下 17 个 Tool 全部由 REST 路由自动生成，无需手动编写 MCP handler。
            </Paragraph>
            {TOOL_CATEGORIES.map((cat) => {
                const tools = MCP_TOOLS.filter((t) => t.category === cat);
                if (tools.length === 0) return null;
                return (
                    <Card
                        key={cat}
                        size="small"
                        title={
                            <Text strong style={{ fontSize: 13 }}>
                                {cat} ({tools.length})
                            </Text>
                        }
                        style={{ marginBottom: 8 }}
                    >
                        {tools.map((t) => (
                            <div
                                key={t.name}
                                style={{
                                    display: "flex",
                                    alignItems: "baseline",
                                    gap: 8,
                                    padding: "4px 0",
                                    borderBottom: "1px solid var(--llm-border)",
                                }}
                            >
                                <Text
                                    code
                                    style={{
                                        fontSize: 12,
                                        minWidth: 200,
                                        flexShrink: 0,
                                    }}
                                >
                                    {t.name}
                                </Text>
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                    {t.description}
                                </Text>
                            </div>
                        ))}
                    </Card>
                );
            })}
        </div>
    );
}
