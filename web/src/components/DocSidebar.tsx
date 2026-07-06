import { Card, Tag, Space, Typography, Empty, Tooltip } from "antd";
import { Link, useParams } from "react-router-dom";
import type { Document, ReferencesData, Highlight } from "../lib/types";
import { parseTags, parseHighlights, parseMetadata } from "../lib/types";
import {
    formatBytes,
    relativeTime,
    formatDate,
    wordCount,
    KIND_COLOR,
    STATUS_COLOR,
    STATUS_LABEL,
} from "../lib/format";

const { Text } = Typography;

function Row({ label, children }: { label: string; children: React.ReactNode }) {
    return (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "4px 0", borderBottom: "1px solid #f5f5f5", gap: 8 }}>
            <Text type="secondary" style={{ fontSize: 12, flexShrink: 0 }}>{label}</Text>
            <div style={{ textAlign: "right", overflow: "hidden" }}>{children}</div>
        </div>
    );
}

function RefItem({ r }: { r: ReferencesData["outgoing"][number] }) {
    const { wsId = "" } = useParams<{ wsId: string }>();
    return (
        <div style={{ padding: "3px 0" }}>
            <Link to={`/w/${wsId}/documents/${r.id}`} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <Tag color={r.type === "cites" ? "blue" : "green"} bordered={false} style={{ fontSize: 10, margin: 0, lineHeight: "16px" }}>
                    {r.type === "cites" ? "引" : "链"}
                </Tag>
                <Text style={{ fontSize: 12, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} ellipsis>
                    {r.title}
                </Text>
                {r.page != null && <Text type="secondary" style={{ fontSize: 10 }}>p{r.page}</Text>}
            </Link>
        </div>
    );
}

interface Props {
    doc: Document;
    references?: ReferencesData | null;
    highlights?: Highlight[];
}

export default function DocSidebar({ doc, references, highlights }: Props) {
    const tags = parseTags(doc.tags);
    const meta = parseMetadata(doc.metadata);
    const hls = highlights || parseHighlights(doc.highlights);
    const refs = references;

    return (
        <div>
            <Card size="small" title="📋 元数据" style={{ marginBottom: 12 }}>
                <Row label="类型">
                    <Tag color={KIND_COLOR[doc.source_kind]} style={{ color: "#fff", border: "none" }}>{doc.source_kind}</Tag>
                </Row>
                <Row label="状态">
                    <Tag color={STATUS_COLOR[doc.status] || "#999"} style={{ color: "#fff", border: "none" }}>
                        {STATUS_LABEL[doc.status] || doc.status}
                    </Tag>
                </Row>
                {doc.entity_type && <Row label="实体"><Tag bordered={false}>{doc.entity_type}</Tag></Row>}
                {doc.domain && <Row label="域"><Tag bordered={false}>{doc.domain}</Tag></Row>}
                {tags.length > 0 && (
                    <Row label="标签">
                        <Space size={4} wrap>
                            {tags.map((t, i) => <Tag key={i} bordered={false}>{t}</Tag>)}
                        </Space>
                    </Row>
                )}
                <Row label="大小">
                    <Text style={{ fontSize: 12 }}>{formatBytes(doc.file_size)} · {wordCount(doc.content)} 词</Text>
                </Row>
                {doc.page_count ? <Row label="页数"><Text>{doc.page_count}</Text></Row> : null}
                <Row label="版本"><Text>v{doc.version}</Text></Row>
                <Row label="更新">
                    <Tooltip title={formatDate(doc.updated_at)}><Text style={{ fontSize: 12 }}>{relativeTime(doc.updated_at)}</Text></Tooltip>
                </Row>
                {meta.source_url != null && String(meta.source_url) !== "" && (
                    <Row label="来源">
                        <a href={String(meta.source_url)} target="_blank" rel="noreferrer" style={{ fontSize: 11, maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "inline-block" }}>
                            🔗 {String(meta.source_url)}
                        </a>
                    </Row>
                )}
                <Row label="路径"><Text style={{ fontSize: 11, fontFamily: "monospace" }}>{doc.relative_path}</Text></Row>
            </Card>

            {refs && (
                <Card size="small" title={`🔗 引用关系 (${refs.outgoing.length + refs.incoming.length})`} style={{ marginBottom: 12 }}>
                    {refs.outgoing.length > 0 && (
                        <>
                            <Text type="secondary" style={{ fontSize: 12 }}>引用了 ({refs.outgoing.length})</Text>
                            {refs.outgoing.map((r) => <RefItem key={r.id} r={r} />)}
                        </>
                    )}
                    {refs.incoming.length > 0 && (
                        <>
                            <Text type="secondary" style={{ fontSize: 12, display: "block", marginTop: 8 }}>被引用 ({refs.incoming.length})</Text>
                            {refs.incoming.map((r) => <RefItem key={r.id} r={r} />)}
                        </>
                    )}
                    {refs.outgoing.length === 0 && refs.incoming.length === 0 && (
                        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="无引用关系" />
                    )}
                </Card>
            )}

            {hls.length > 0 && (
                <Card size="small" title={`🖊 高亮 (${hls.length})`}>
                    {hls.map((h, i) => (
                        <div key={i} style={{ padding: "4px 0", borderBottom: "1px solid #f5f5f5" }}>
                            <Text style={{ fontSize: 12, background: "#ffe58f", padding: "0 2px", borderRadius: 2 }}>
                                {String(h.text || "").slice(0, 60) || "(无文本)"}
                            </Text>
                            {h.note && <div><Text type="secondary" style={{ fontSize: 11 }}>📝 {String(h.note)}</Text></div>}
                        </div>
                    ))}
                </Card>
            )}
        </div>
    );
}
