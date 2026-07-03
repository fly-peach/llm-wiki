import { useState } from "react";
import { Input, Button, Card, List, Typography, message, Space, Popconfirm, Tag } from "antd";
import { PlusOutlined, DeleteOutlined, FolderOpenOutlined, CheckCircleOutlined } from "@ant-design/icons";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace-context";
import { relativeTime } from "../lib/format";

const { Text } = Typography;

export default function WorkspaceManager() {
    const { workspaces, current, switchTo, refresh, loaded } = useWorkspace();
    const [newPath, setNewPath] = useState("");
    const [newName, setNewName] = useState("");
    const [creating, setCreating] = useState(false);

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
        </div>
    );
}
