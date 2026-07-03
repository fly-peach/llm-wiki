import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
    Card,
    Table,
    Button,
    Space,
    Tag,
    Input,
    Select,
    Popconfirm,
    Modal,
    message,
    Segmented,
    Typography,
    Empty,
    Tooltip,
} from "antd";
import {
    PlusOutlined,
    DeleteOutlined,
    UploadOutlined,
    ReloadOutlined,
    SyncOutlined,
} from "@ant-design/icons";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace-context";
import type { Document, SourceKind } from "../lib/types";
import { parseTags } from "../lib/types";
import {
    formatBytes,
    relativeTime,
    KIND_COLOR,
    STATUS_COLOR,
    STATUS_LABEL,
} from "../lib/format";
import FileTree from "../components/FileTree";

const { Text } = Typography;

const KINDS: { value: "" | SourceKind; label: string }[] = [
    { value: "", label: "全部" },
    { value: "wiki", label: "Wiki" },
    { value: "raw", label: "原始文档" },
    { value: "asset", label: "资产" },
];

const STATUS_OPTS = ["", "ready", "stale", "pending", "processing", "failed"];

export default function Documents() {
    const { current } = useWorkspace();
    const [docs, setDocs] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [filterKind, setFilterKind] = useState<"" | SourceKind>("");
    const [filterStatus, setFilterStatus] = useState("");
    const [filterEntity, setFilterEntity] = useState("");
    const [keyword, setKeyword] = useState("");
    const [selectedDir, setSelectedDir] = useState("");
    const [selectedKeys, setSelectedKeys] = useState<React.Key[]>([]);

    // 新建笔记
    const [noteOpen, setNoteOpen] = useState(false);
    const [noteForm, setNoteForm] = useState({ filename: "", title: "", content: "" });

    // 上传
    const [uploadOpen, setUploadOpen] = useState(false);
    const [uploadFile, setUploadFile] = useState<File | null>(null);
    const [uploadPath, setUploadPath] = useState("/");

    const load = async () => {
        setLoading(true);
        try {
            const r = await api.listDocuments({ limit: 500 });
            setDocs(r.documents);
        } catch {
            message.error("加载失败");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (!current) return;
        load();
    }, [current]);

    const entityOptions = useMemo(() => {
        const set = new Set<string>();
        docs.forEach((d) => d.entity_type && set.add(d.entity_type));
        return [...set];
    }, [docs]);

    const filtered = useMemo(() => {
        return docs.filter((d) => {
            if (filterKind && d.source_kind !== filterKind) return false;
            if (filterStatus && d.status !== filterStatus) return false;
            if (filterEntity && d.entity_type !== filterEntity) return false;
            if (selectedDir && !d.relative_path.startsWith(selectedDir + "/")) return false;
            if (keyword.trim()) {
                const kw = keyword.toLowerCase();
                const t = (d.title || d.filename || "").toLowerCase();
                if (!t.includes(kw)) return false;
            }
            return true;
        });
    }, [docs, filterKind, filterStatus, filterEntity, selectedDir, keyword]);

    const handleBulkDelete = async () => {
        await api.bulkDelete(selectedKeys.map(String));
        message.success(`已删除 ${selectedKeys.length} 篇`);
        setSelectedKeys([]);
        load();
    };

    const handleDelete = async (id: string) => {
        await api.deleteDocument(id);
        message.success("已删除");
        load();
    };

    const handleCreateNote = async () => {
        if (!noteForm.filename.trim()) {
            message.warning("请填写文件名");
            return;
        }
        await api.createNote({
            filename: noteForm.filename,
            title: noteForm.title || undefined,
            content: noteForm.content,
        });
        message.success("笔记已创建");
        setNoteOpen(false);
        setNoteForm({ filename: "", title: "", content: "" });
        load();
    };

    const handleReindex = async () => {
        try {
            const msg = message.loading("正在重建索引...", 0);
            const r = await api.reindex();
            msg();
            message.success(`索引完成: ${r.indexed} 个文件, 跳过 ${r.skipped} 个`);
            load();
        } catch {
            message.error("索引失败");
        }
    };

    const handleUpload = async () => {
        if (!uploadFile) {
            message.warning("请选择文件");
            return;
        }
        await api.upload(uploadFile, uploadPath);
        message.success("上传成功");
        setUploadOpen(false);
        setUploadFile(null);
        load();
    };

    const columns = [
        {
            title: "标题",
            dataIndex: "title",
            render: (_: unknown, d: Document) => (
                <Link to={`/documents/${d.id}`} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span
                        style={{
                            display: "inline-block",
                            width: 7,
                            height: 7,
                            borderRadius: "50%",
                            background: KIND_COLOR[d.source_kind] || "#999",
                            flexShrink: 0,
                        }}
                    />
                    <span>{d.title || d.filename}</span>
                </Link>
            ),
        },
        {
            title: "类型",
            dataIndex: "source_kind",
            width: 90,
            render: (k: string) => <Tag color={KIND_COLOR[k]} style={{ color: "#fff", border: "none" }}>{k}</Tag>,
        },
        {
            title: "状态",
            dataIndex: "status",
            width: 90,
            render: (s: string) => (
                <Tag color={STATUS_COLOR[s] || "#999"} style={{ color: "#fff", border: "none" }}>
                    {STATUS_LABEL[s] || s}
                </Tag>
            ),
        },
        {
            title: "实体",
            dataIndex: "entity_type",
            width: 100,
            render: (e: string | null) => (e ? <Tag bordered={false}>{e}</Tag> : <Text type="secondary">—</Text>),
        },
        {
            title: "标签",
            dataIndex: "tags",
            render: (t: string) => {
                const tags = parseTags(t);
                if (!tags.length) return <Text type="secondary">—</Text>;
                return (
                    <Space size={4} wrap>
                        {tags.slice(0, 3).map((tag, i) => (
                            <Tag key={i} bordered={false} style={{ fontSize: 11 }}>{tag}</Tag>
                        ))}
                        {tags.length > 3 && <Text type="secondary">+{tags.length - 3}</Text>}
                    </Space>
                );
            },
        },
        {
            title: "更新",
            dataIndex: "updated_at",
            width: 110,
            render: (t: string) => <Tooltip title={t}>{relativeTime(t)}</Tooltip>,
        },
        {
            title: "大小",
            dataIndex: "file_size",
            width: 80,
            render: (s: number) => <Text type="secondary">{formatBytes(s)}</Text>,
        },
        {
            title: "操作",
            width: 80,
            render: (_: unknown, d: Document) => (
                <Popconfirm title="确定删除?" onConfirm={() => handleDelete(d.id)}>
                    <Button type="text" danger icon={<DeleteOutlined />} size="small" />
                </Popconfirm>
            ),
        },
    ];

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h1 className="page-title" style={{ margin: 0 }}>
                    文档列表
                    <Text type="secondary" style={{ fontSize: 14, fontWeight: 400, marginLeft: 8 }}>
                        {filtered.length} / {docs.length}
                    </Text>
                </h1>
                <Space>
                    <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
                    <Button icon={<SyncOutlined />} onClick={handleReindex}>重建索引</Button>
                    <Button icon={<UploadOutlined />} onClick={() => setUploadOpen(true)}>上传</Button>
                    <Button type="primary" icon={<PlusOutlined />} onClick={() => setNoteOpen(true)}>新建笔记</Button>
                </Space>
            </div>

            <div style={{ display: "flex", gap: 16 }}>
                <Card size="small" style={{ width: 240, height: "calc(100vh - 200px)", minHeight: 400 }}>
                    {docs.length === 0 && !loading ? (
                        <Empty description="暂无文档" />
                    ) : (
                        <FileTree docs={docs} selectedDir={selectedDir} onDirSelect={setSelectedDir} />
                    )}
                </Card>

                <div style={{ flex: 1, minWidth: 0 }}>
                    <Card size="small" style={{ marginBottom: 12 }}>
                        <Space wrap>
                            <Segmented
                                value={filterKind}
                                onChange={(v) => setFilterKind(v as "" | SourceKind)}
                                options={KINDS.map((k) => ({ label: k.label, value: k.value }))}
                            />
                            <Select
                                placeholder="状态"
                                allowClear
                                value={filterStatus || undefined}
                                onChange={(v) => setFilterStatus(v || "")}
                                style={{ width: 120 }}
                                options={STATUS_OPTS.filter(Boolean).map((s) => ({ value: s, label: STATUS_LABEL[s] || s }))}
                            />
                            <Select
                                placeholder="实体类型"
                                allowClear
                                value={filterEntity || undefined}
                                onChange={(v) => setFilterEntity(v || "")}
                                style={{ width: 140 }}
                                options={entityOptions.map((e) => ({ value: e, label: e }))}
                            />
                            <Input.Search
                                placeholder="按标题搜索"
                                allowClear
                                value={keyword}
                                onChange={(e) => setKeyword(e.target.value)}
                                style={{ width: 200 }}
                            />
                            {selectedKeys.length > 0 && (
                                <Popconfirm title={`删除选中的 ${selectedKeys.length} 篇?`} onConfirm={handleBulkDelete}>
                                    <Button danger icon={<DeleteOutlined />}>
                                        批量删除({selectedKeys.length})
                                    </Button>
                                </Popconfirm>
                            )}
                            {selectedDir && (
                                <Tag closable onClose={() => setSelectedDir("")} color="blue">
                                    目录: {selectedDir}
                                </Tag>
                            )}
                        </Space>
                    </Card>

                    <Card size="small">
                        <Table<Document>
                            rowKey="id"
                            loading={loading}
                            dataSource={filtered}
                            columns={columns}
                            size="small"
                            rowSelection={{
                                selectedRowKeys: selectedKeys,
                                onChange: setSelectedKeys,
                            }}
                            pagination={{ pageSize: 50, showSizeChanger: false, size: "small" }}
                        />
                    </Card>
                </div>
            </div>

            {/* 新建笔记 Modal */}
            <Modal
                title="新建笔记"
                open={noteOpen}
                onOk={handleCreateNote}
                onCancel={() => setNoteOpen(false)}
                okText="创建"
                cancelText="取消"
                width={640}
            >
                <Space direction="vertical" style={{ width: "100%" }}>
                    <Input
                        addonBefore="文件名"
                        placeholder="attention.md"
                        value={noteForm.filename}
                        onChange={(e) => setNoteForm({ ...noteForm, filename: e.target.value })}
                    />
                    <Input
                        addonBefore="标题"
                        placeholder="(可选) Attention 机制"
                        value={noteForm.title}
                        onChange={(e) => setNoteForm({ ...noteForm, title: e.target.value })}
                    />
                    <Input.TextArea
                        rows={12}
                        placeholder="# 页面标题&#10;正文内容… 用 [^1]: 标注引用,[text](page.md) 交叉链接"
                        value={noteForm.content}
                        onChange={(e) => setNoteForm({ ...noteForm, content: e.target.value })}
                        style={{ fontFamily: "monospace, Consolas, monospace", fontSize: 13 }}
                    />
                </Space>
            </Modal>

            {/* 上传 Modal */}
            <Modal
                title="上传文件"
                open={uploadOpen}
                onOk={handleUpload}
                onCancel={() => setUploadOpen(false)}
                okText="上传"
                cancelText="取消"
            >
                <Space direction="vertical" style={{ width: "100%" }}>
                    <Input
                        addonBefore="目标目录"
                        value={uploadPath}
                        onChange={(e) => setUploadPath(e.target.value)}
                    />
                    <input
                        type="file"
                        onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                        style={{ width: "100%" }}
                    />
                    {uploadFile && (
                        <Text type="secondary">
                            {uploadFile.name} ({formatBytes(uploadFile.size)})
                        </Text>
                    )}
                </Space>
            </Modal>
        </div>
    );
}
