import { useEffect, useState } from "react";
import { Button, Card, Input, List, Typography, message, Tabs, Tag } from "antd";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace-context";
import type { TemplateInfo } from "../lib/types";
import MdRenderer from "../components/MdRenderer";

const { Text } = Typography;
const { TextArea } = Input;

export default function SchemaEditor() {
    const { current } = useWorkspace();
    const [content, setContent] = useState("");
    const [templates, setTemplates] = useState<TemplateInfo[]>([]);
    const [saving, setSaving] = useState(false);
    const [activeTab, setActiveTab] = useState("preview");

    useEffect(() => {
        if (!current) return;
        api.getSchema().then((r) => setContent(r.content)).catch(() => {});
        api.getTemplates().then((r) => setTemplates(r.types)).catch(() => {});
    }, [current]);

    const handleSave = async () => {
        setSaving(true);
        try {
            await api.updateSchema(content);
            message.success("保存成功");
        } catch (e: any) {
            message.error(e.message || "保存失败");
        } finally {
            setSaving(false);
        }
    };

    const handleTemplate = async (type: string) => {
        const d = await api.getTemplate(type);
        setContent((prev) => prev + "\n\n" + d.template);
        message.success(`已追加模板: ${type}`);
        setActiveTab("preview");
    };

    return (
        <div>
            <h1 className="page-title">规范编辑器</h1>
            <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
                <Card
                    title="SCHEMA.md"
                    size="small"
                    style={{ flex: 1, minWidth: 0 }}
                    extra={
                        <Button type="primary" onClick={handleSave} loading={saving}>
                            保存
                        </Button>
                    }
                >
                    <TextArea
                        rows={24}
                        value={content}
                        onChange={(e) => setContent(e.target.value)}
                        style={{ fontFamily: "monospace, Consolas, monospace", fontSize: 13 }}
                    />
                </Card>

                <Card size="small" style={{ flex: 1, minWidth: 0 }}>
                    <Tabs
                        activeKey={activeTab}
                        onChange={setActiveTab}
                        items={[
                            {
                                key: "preview",
                                label: "预览",
                                children: (
                                    <div style={{ maxHeight: "70vh", overflow: "auto" }}>
                                        <MdRenderer content={content} />
                                    </div>
                                ),
                            },
                            {
                                key: "templates",
                                label: `实体模板 (${templates.length})`,
                                children: (
                                    <List
                                        size="small"
                                        dataSource={templates}
                                        renderItem={(t) => (
                                            <List.Item>
                                                <a onClick={() => handleTemplate(t.key)} style={{ fontSize: 13 }}>
                                                    {t.label} <Tag bordered={false} style={{ fontSize: 10 }}>{t.key}</Tag>
                                                </a>
                                            </List.Item>
                                        )}
                                    />
                                ),
                            },
                        ]}
                    />
                </Card>
            </div>
        </div>
    );
}
