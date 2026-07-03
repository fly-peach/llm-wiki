import { useState } from "react";
import { Link } from "react-router-dom";
import { Input, Button, Card, List, Typography, Tag, Empty, Space } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace-context";
import type { SearchResult } from "../lib/types";
import { highlightText, KIND_COLOR, truncate } from "../lib/format";

const { Text } = Typography;

export default function SearchPage() {
    const { current } = useWorkspace();
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<SearchResult[]>([]);
    const [searched, setSearched] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSearch = async () => {
        if (!query.trim()) return;
        setLoading(true);
        try {
            const r = await api.search(query);
            setResults(r.results || []);
            setSearched(true);
        } catch {
            setResults([]);
        } finally {
            setLoading(false);
        }
    };

    const linkFor = (r: SearchResult) =>
        `/documents/${r.doc_id}?chunk=${r.chunk_index ?? 0}&query=${encodeURIComponent(query)}`;

    return (
        <div style={{ maxWidth: 900 }}>
            <h1 className="page-title">搜索</h1>
            <Space.Compact style={{ width: "100%", marginBottom: 16 }}>
                <Input
                    prefix={<SearchOutlined />}
                    placeholder="搜索文档内容…"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onPressEnter={handleSearch}
                    size="large"
                    allowClear
                />
                <Button type="primary" size="large" onClick={handleSearch} loading={loading}>
                    搜索
                </Button>
            </Space.Compact>

            {searched && (
                <Text type="secondary" style={{ display: "block", marginBottom: 12 }}>
                    {results.length} 条结果 {query && <> — "{query}"</>}
                </Text>
            )}

            {searched && results.length === 0 && (
                <Empty description="没有找到结果，试试其他关键词" />
            )}

            <List
                dataSource={results}
                renderItem={(r, i) => (
                    <Card
                        size="small"
                        hoverable
                        key={i}
                        style={{ marginBottom: 8 }}
                    >
                        <Link to={linkFor(r)} style={{ textDecoration: "none" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                                <span
                                    style={{
                                        display: "inline-block",
                                        width: 8,
                                        height: 8,
                                        borderRadius: "50%",
                                        background: KIND_COLOR[r.source_kind] || "#999",
                                    }}
                                />
                                <Text strong>{r.title || r.filename}</Text>
                                <Tag color={KIND_COLOR[r.source_kind]} style={{ color: "#fff", border: "none" }}>
                                    {r.source_kind}
                                </Tag>
                                {r.chunk_index != null && (
                                    <Text type="secondary" style={{ fontSize: 11 }}>
                                        chunk {r.chunk_index}
                                    </Text>
                                )}
                            </div>
                            {r.header_breadcrumb && (
                                <Text type="secondary" style={{ fontSize: 11, display: "block", marginBottom: 4 }}>
                                    📍 {r.header_breadcrumb}
                                </Text>
                            )}
                            <div
                                style={{ color: "#555", fontSize: 13, lineHeight: 1.7 }}
                                dangerouslySetInnerHTML={{
                                    __html: highlightText(truncate(r.chunk_content, 400), query),
                                }}
                            />
                        </Link>
                    </Card>
                )}
            />
        </div>
    );
}
