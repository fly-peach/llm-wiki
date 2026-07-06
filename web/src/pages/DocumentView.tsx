import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import {
    Card,
    Button,
    Space,
    Tag,
    Typography,
    message,
    Popconfirm,
    Spin,
    Tooltip,
} from "antd";
import {
    ArrowLeftOutlined,
    EditOutlined,
    DeleteOutlined,
    SaveOutlined,
    CloseOutlined,
} from "@ant-design/icons";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace-context";
import type { Document, ReferencesData, Highlight } from "../lib/types";
import { parseHighlights } from "../lib/types";
import { KIND_COLOR, STATUS_LABEL, relativeTime } from "../lib/format";
import MdRenderer from "../components/MdRenderer";
import DocSidebar from "../components/DocSidebar";
import Toc from "../components/Toc";
import NoteEditor from "../components/NoteEditor";

const { Text } = Typography;

export default function DocumentView() {
    const { id } = useParams<{ id: string }>();
    const nav = useNavigate();
    const [sp] = useSearchParams();
    const { current } = useWorkspace();

    const [doc, setDoc] = useState<Document | null>(null);
    const [content, setContent] = useState("");
    const [references, setReferences] = useState<ReferencesData | null>(null);
    const [highlights, setHighlights] = useState<Highlight[]>([]);
    const [allDocs, setAllDocs] = useState<Document[]>([]);
    const [editing, setEditing] = useState(false);
    const [editText, setEditText] = useState("");
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        if (!id || !current) return;
        api.getDocument(id).then(setDoc).catch(() => {});
        api.getDocumentContent(id).then((r) => {
            setContent(r.content);
            setEditText(r.content);
        });
        api.getReferences(id).then(setReferences).catch(() => setReferences(null));
        api
            .getHighlights(id)
            .then((r) => setHighlights(parseHighlights(JSON.stringify(r.highlights))))
            .catch(() => setHighlights([]));
        api.listDocuments({ limit: 500 }).then((r) => setAllDocs(r.documents)).catch(() => {});
    }, [id, current]);

    const linkMaps = useMemo(() => {
        const wiki = new Map<string, string>();
        const src = new Map<string, string>();
        allDocs.forEach((d) => {
            const fname = d.filename.toLowerCase();
            const stemName = fname.replace(/\.[^.]+$/, "");
            if (d.source_kind === "wiki") {
                wiki.set(fname, d.id);
                wiki.set(stemName, d.id);
                wiki.set(stemName + ".md", d.id);
            } else {
                src.set(fname, d.id);
                src.set(stemName, d.id);
            }
        });
        return { wiki, src };
    }, [allDocs]);

    const handleSave = async () => {
        if (!id || !doc) return;
        setSaving(true);
        try {
            await api.updateContent(id, editText, doc.version);
            setContent(editText);
            setEditing(false);
            message.success("保存成功");
            const nd = await api.getDocument(id);
            setDoc(nd);
        } catch (e: any) {
            message.error(e.message || "保存失败（可能版本冲突，请刷新）");
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async () => {
        if (!id) return;
        await api.deleteDocument(id);
        nav(`/w/${current}/documents`);
        message.success("已删除");
    };

    const queryHint = sp.get("query") || "";

    if (!doc) {
        return (
            <div style={{ textAlign: "center", padding: 80 }}>
                <Spin size="large" />
            </div>
        );
    }

    return (
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
            <div style={{ flex: 1, minWidth: 0 }}>
                <Button
                    type="link"
                    icon={<ArrowLeftOutlined />}
                    onClick={() => nav(-1)}
                    style={{ padding: "0 0 8px" }}
                >
                    返回
                </Button>
                <Card>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16, alignItems: "flex-start", gap: 12 }}>
                        <div style={{ flex: 1, minWidth: 0 }}>
                            <Text strong style={{ fontSize: 22, wordBreak: "break-word" }}>
                                {doc.title || doc.filename}
                            </Text>
                            <div style={{ marginTop: 6 }}>
                                <Space size={6} wrap>
                                    <Tag color={KIND_COLOR[doc.source_kind]} style={{ color: "#fff", border: "none" }}>
                                        {doc.source_kind}
                                    </Tag>
                                    <Tag bordered={false}>{doc.file_type}</Tag>
                                    {doc.entity_type && <Tag bordered={false}>{doc.entity_type}</Tag>}
                                    <Text type="secondary" style={{ fontSize: 12 }}>{doc.relative_path}</Text>
                                    <Tooltip title={doc.updated_at}>
                                        <Text type="secondary" style={{ fontSize: 12 }}>· 更新 {relativeTime(doc.updated_at)}</Text>
                                    </Tooltip>
                                </Space>
                            </div>
                            {queryHint && (
                                <div style={{ marginTop: 8 }}>
                                    <Tag color="gold">来自搜索: {queryHint}</Tag>
                                </div>
                            )}
                        </div>
                        <Space>
                            {editing ? (
                                <>
                                    <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
                                        保存
                                    </Button>
                                    <Button
                                        icon={<CloseOutlined />}
                                        onClick={() => {
                                            setEditing(false);
                                            setEditText(content);
                                        }}
                                    >
                                        取消
                                    </Button>
                                </>
                            ) : (
                                <>
                                    <Button icon={<EditOutlined />} onClick={() => setEditing(true)}>
                                        编辑
                                    </Button>
                                    <Popconfirm title="确定删除?" onConfirm={handleDelete}>
                                        <Button danger icon={<DeleteOutlined />}>
                                            删除
                                        </Button>
                                    </Popconfirm>
                                </>
                            )}
                        </Space>
                    </div>

                    {editing ? (
                        <NoteEditor value={editText} onChange={setEditText} />
                    ) : (
                        <MdRenderer content={content} wikiLinkMap={linkMaps.wiki} sourceMap={linkMaps.src} />
                    )}
                </Card>
            </div>

            <div style={{ width: 280, flexShrink: 0, position: "sticky", top: 64 }}>
                <Card size="small" style={{ marginBottom: 12 }}>
                    <Toc md={content} />
                </Card>
                <DocSidebar doc={doc} references={references} highlights={highlights} />
            </div>
        </div>
    );
}
