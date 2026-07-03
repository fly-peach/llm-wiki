import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Card, Row, Col, Statistic, Button, Space, Tag, Typography, List, Empty, Spin } from "antd";
import {
    FileTextOutlined,
    DatabaseOutlined,
    FileOutlined,
    AppstoreOutlined,
    WarningOutlined,
    ClockCircleOutlined,
    SearchOutlined,
    ApartmentOutlined,
    ReloadOutlined,
    ApiOutlined,
} from "@ant-design/icons";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace-context";
import type { Document } from "../lib/types";
import { relativeTime, KIND_COLOR, KIND_LABEL, STATUS_COLOR, STATUS_LABEL } from "../lib/format";

const { Text } = Typography;

const ENTITY_PALETTE = ["#4f46e5", "#1677ff", "#52c41a", "#fa8c16", "#eb2f96", "#722ed1", "#13c2c2", "#fa541c"];

export default function Dashboard() {
    const { workspaces, current, refresh } = useWorkspace();
    const [docs, setDocs] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [apiOk, setApiOk] = useState<boolean | null>(null);

    useEffect(() => {
        if (!current) return;
        setLoading(true);
        api.listDocuments({ limit: 500 })
            .then((r) => setDocs(r.documents))
            .catch(() => {})
            .finally(() => setLoading(false));
        api.health().then(() => setApiOk(true)).catch(() => setApiOk(false));
    }, [current]);

    const wsName = workspaces.find((w) => w.id === current)?.name || "—";

    const stats = useMemo(() => {
        const byKind: Record<string, number> = { wiki: 0, raw: 0, asset: 0 };
        const byEntity = new Map<string, number>();
        docs.forEach((d) => {
            byKind[d.source_kind] = (byKind[d.source_kind] || 0) + 1;
            if (d.entity_type) byEntity.set(d.entity_type, (byEntity.get(d.entity_type) || 0) + 1);
        });
        const pending = docs.filter((d) => d.status && d.status !== "ready" && d.status !== "deleted");
        const recent = [...docs]
            .sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""))
            .slice(0, 8);
        return {
            byKind,
            byEntity: [...byEntity.entries()].sort((a, b) => b[1] - a[1]),
            pending,
            recent,
        };
    }, [docs]);

    const maxEntity = stats.byEntity[0]?.[1] || 1;

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                <h1 className="page-title" style={{ margin: 0 }}>
                    工作台 — {wsName}
                </h1>
                <Space>
                    {apiOk !== null && (
                        <Tag color={apiOk ? "green" : "red"}>
                            <ApiOutlined /> API {apiOk ? "正常" : "异常"}
                        </Tag>
                    )}
                    <Button icon={<ReloadOutlined />} onClick={refresh}>刷新</Button>
                </Space>
            </div>

            {loading ? (
                <div style={{ textAlign: "center", padding: 80 }}><Spin size="large" /></div>
            ) : (
                <>
                    <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={6}>
                            <Card size="small"><Statistic title="总文档" value={docs.length} prefix={<FileTextOutlined />} /></Card>
                        </Col>
                        <Col span={6}>
                            <Card size="small"><Statistic title="Wiki 页" value={stats.byKind.wiki} prefix={<DatabaseOutlined />} valueStyle={{ color: KIND_COLOR.wiki }} /></Card>
                        </Col>
                        <Col span={6}>
                            <Card size="small"><Statistic title="原始文档" value={stats.byKind.raw} prefix={<FileOutlined />} valueStyle={{ color: KIND_COLOR.raw }} /></Card>
                        </Col>
                        <Col span={6}>
                            <Card size="small"><Statistic title="资产" value={stats.byKind.asset} prefix={<AppstoreOutlined />} valueStyle={{ color: KIND_COLOR.asset }} /></Card>
                        </Col>
                    </Row>

                    <Row gutter={16}>
                        <Col span={16}>
                            <Card
                                size="small"
                                title={<Space><WarningOutlined /> 待处理 ({stats.pending.length})</Space>}
                                style={{ marginBottom: 16 }}
                            >
                                {stats.pending.length === 0 ? (
                                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="全部就绪" />
                                ) : (
                                    <List
                                        size="small"
                                        dataSource={stats.pending}
                                        renderItem={(d) => (
                                            <List.Item>
                                                <Link to={`/documents/${d.id}`} style={{ flex: 1, display: "flex", alignItems: "center", gap: 8 }}>
                                                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: KIND_COLOR[d.source_kind] || "#999", display: "inline-block" }} />
                                                    <Text style={{ flex: 1 }}>{d.title || d.filename}</Text>
                                                    <Tag color={STATUS_COLOR[d.status] || "#999"} style={{ color: "#fff", border: "none" }}>
                                                        {STATUS_LABEL[d.status] || d.status}
                                                    </Tag>
                                                    <Text type="secondary" style={{ fontSize: 11 }}>{relativeTime(d.updated_at)}</Text>
                                                </Link>
                                            </List.Item>
                                        )}
                                    />
                                )}
                            </Card>

                            <Card size="small" title={<Space><ClockCircleOutlined /> 最近活动</Space>}>
                                <List
                                    size="small"
                                    dataSource={stats.recent}
                                    renderItem={(d) => (
                                        <List.Item>
                                            <Link to={`/documents/${d.id}`} style={{ flex: 1, display: "flex", alignItems: "center", gap: 8 }}>
                                                <span style={{ width: 7, height: 7, borderRadius: "50%", background: KIND_COLOR[d.source_kind] || "#999", display: "inline-block" }} />
                                                <Text style={{ flex: 1 }} ellipsis>{d.title || d.filename}</Text>
                                                <Text type="secondary" style={{ fontSize: 11 }}>{relativeTime(d.updated_at)}</Text>
                                            </Link>
                                        </List.Item>
                                    )}
                                />
                            </Card>
                        </Col>

                        <Col span={8}>
                            <Card size="small" title="实体类型分布" style={{ marginBottom: 16 }}>
                                {stats.byEntity.length === 0 ? (
                                    <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无实体" />
                                ) : (
                                    stats.byEntity.map(([et, c], i) => (
                                        <div key={et} style={{ marginBottom: 10 }}>
                                            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                                                <Text style={{ fontSize: 13 }}>{et}</Text>
                                                <Text type="secondary" style={{ fontSize: 12 }}>{c}</Text>
                                            </div>
                                            <div style={{ height: 6, background: "#f0f0f0", borderRadius: 3 }}>
                                                <div style={{
                                                    width: `${(c / maxEntity) * 100}%`,
                                                    height: "100%",
                                                    background: ENTITY_PALETTE[i % ENTITY_PALETTE.length],
                                                    borderRadius: 3,
                                                }} />
                                            </div>
                                        </div>
                                    ))
                                )}
                            </Card>

                            <Card size="small" title="快速入口">
                                <Space wrap>
                                    <Link to="/documents"><Button icon={<FileTextOutlined />}>浏览文档</Button></Link>
                                    <Link to="/search"><Button icon={<SearchOutlined />}>搜索</Button></Link>
                                    <Link to="/graph"><Button icon={<ApartmentOutlined />}>图谱</Button></Link>
                                </Space>
                            </Card>
                        </Col>
                    </Row>
                </>
            )}
        </div>
    );
}
