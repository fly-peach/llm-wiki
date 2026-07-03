import { useState } from "react";
import { Card, Input, Button, Typography, message } from "antd";
import { FolderOpenOutlined } from "@ant-design/icons";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace-context";

const { Text, Title } = Typography;

export default function Onboarding() {
    const { refresh, switchTo } = useWorkspace();
    const [path, setPath] = useState("");
    const [creating, setCreating] = useState(false);

    const handleCreate = async () => {
        if (!path.trim()) {
            message.warning("请填写工作区路径");
            return;
        }
        setCreating(true);
        try {
            const ws = await api.createWorkspace(path.trim());
            await refresh();
            await switchTo(ws.id);
            message.success("工作区已就绪");
        } catch (e: any) {
            message.error(e.message || "创建失败");
        } finally {
            setCreating(false);
        }
    };

    return (
        <div
            style={{
                minHeight: "100vh",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "var(--llm-bg)",
                padding: 24,
            }}
        >
            <Card style={{ width: 460, boxShadow: "0 4px 24px rgba(0,0,0,0.06)" }} bordered={false}>
                <div style={{ textAlign: "center", marginBottom: 24 }}>
                    <div style={{ fontSize: 40, marginBottom: 8 }}>🧠</div>
                    <Title level={3} style={{ margin: 0 }}>
                        欢迎使用 LLM Wiki
                    </Title>
                    <Text type="secondary">先创建一个工作区（磁盘文件夹）即可开始</Text>
                </div>

                <div style={{ marginBottom: 12 }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        工作区路径
                    </Text>
                    <Input
                        prefix={<FolderOpenOutlined />}
                        placeholder="E:/my-wiki"
                        value={path}
                        onChange={(e) => setPath(e.target.value)}
                        onPressEnter={handleCreate}
                        size="large"
                        autoFocus
                    />
                </div>

                <Button type="primary" block size="large" loading={creating} onClick={handleCreate}>
                    创建并进入
                </Button>

                <div
                    style={{
                        marginTop: 16,
                        padding: 12,
                        background: "#fffbe6",
                        borderRadius: 6,
                        fontSize: 12,
                        color: "#8a6d3b",
                        lineHeight: 1.6,
                    }}
                >
                    ⚠️ 路径别选项目根目录，否则会把 .git / node_modules 等都索引进去。
                    <br />
                    工作区会自动创建 wiki/ 子目录，原始文档直接放在工作区根目录即可。
                </div>
            </Card>
        </div>
    );
}
