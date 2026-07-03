import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Card, Button, Statistic, Row, Col, Spin, Typography, Space, Checkbox, Input, Empty, Tag } from "antd";
import * as d3 from "d3";
import { api } from "../lib/api";
import { useWorkspace } from "../lib/workspace-context";
import type { GraphData, GraphNode } from "../lib/types";
import { KIND_COLOR, STATUS_LABEL } from "../lib/format";

const { Text } = Typography;

interface HoverInfo {
    id: string;
    title: string;
    source_kind: string;
    outDeg: number;
    inDeg: number;
    x: number;
    y: number;
}

export default function GraphView() {
    const { current } = useWorkspace();
    const [data, setData] = useState<GraphData | null>(null);
    const [loading, setLoading] = useState(true);
    const [hovered, setHovered] = useState<HoverInfo | null>(null);
    const [focusId, setFocusId] = useState<string | null>(null);
    const [listSearch, setListSearch] = useState("");
    const [filter, setFilter] = useState({
        wiki: true, raw: true, asset: true, cites: true, links_to: true,
    });

    const svgRef = useRef<SVGSVGElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const nodeSelRef = useRef<d3.Selection<SVGGElement, any, any, any> | null>(null);
    const linkSelRef = useRef<d3.Selection<SVGLineElement, any, any, any> | null>(null);
    const simRef = useRef<d3.Simulation<any, any> | null>(null);

    // 度数
    const degrees = useMemo(() => {
        const out = new Map<string, number>();
        const ind = new Map<string, number>();
        (data?.edges || []).forEach((e) => {
            out.set(e.source, (out.get(e.source) || 0) + 1);
            ind.set(e.target, (ind.get(e.target) || 0) + 1);
        });
        return { out, ind };
    }, [data]);

    const filteredData = useMemo(() => {
        if (!data) return { nodes: [], edges: [] };
        const nodes = data.nodes.filter((n) => filter[n.source_kind as keyof typeof filter] ?? true);
        const nodeIds = new Set(nodes.map((n) => n.id));
        const edges = data.edges.filter(
            (e) => (filter[e.type] ?? true) && nodeIds.has(e.source) && nodeIds.has(e.target),
        );
        return { nodes, edges };
    }, [data, filter]);

    useEffect(() => {
        if (!current) return;
        api.getGraph().then((d) => { setData(d); setLoading(false); }).catch(() => setLoading(false));
    }, [current]);

    useEffect(() => {
        if (!data || !svgRef.current) return;
        renderGraph(filteredData);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [filteredData]);

    // 聚焦高亮
    useEffect(() => {
        const nodes = nodeSelRef.current;
        const links = linkSelRef.current;
        if (!nodes || !links) return;
        if (!focusId) {
            nodes.transition().duration(200).style("opacity", 1);
            links.transition().duration(200).style("opacity", 0.55);
        } else {
            const neighbors = new Set<string>([focusId]);
            filteredData.edges.forEach((e) => {
                if (e.source === focusId) neighbors.add(e.target);
                if (e.target === focusId) neighbors.add(e.source);
            });
            nodes.transition().duration(200).style("opacity", (d: any) => (neighbors.has(d.id) ? 1 : 0.12));
            links.transition().duration(200).style("opacity", (e: any) =>
                e.source.id === focusId || e.target.id === focusId ? 0.9 : 0.04,
            );
        }
    }, [focusId, filteredData]);

    const handleRebuild = async () => {
        setLoading(true);
        await api.rebuildGraph();
        const d = await api.getGraph();
        setData(d);
        setLoading(false);
    };

    const renderGraph = (fd: { nodes: GraphNode[]; edges: any[] }) => {
        const svgEl = svgRef.current!;
        const svg = d3.select(svgEl);
        svg.selectAll("*").remove();
        simRef.current?.stop();

        const width = containerRef.current?.clientWidth || 800;
        const height = 520;

        const nodes: any[] = fd.nodes.map((n) => ({ ...n }));
        const edges: any[] = fd.edges
            .map((e) => ({
                source: nodes.find((n) => n.id === e.source),
                target: nodes.find((n) => n.id === e.target),
                type: e.type,
            }))
            .filter((e) => e.source && e.target);

        if (nodes.length === 0) {
            svg.append("text")
                .attr("x", width / 2)
                .attr("y", height / 2)
                .attr("text-anchor", "middle")
                .attr("fill", "#999")
                .text("暂无图谱数据，上传文件后重建");
            return;
        }

        const sim = d3
            .forceSimulation(nodes)
            .force("link", d3.forceLink(edges).distance(110).id((d: any) => d.id))
            .force("charge", d3.forceManyBody().strength(-380))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collide", d3.forceCollide(32));
        simRef.current = sim;

        const g = svg.append("g");

        // 边
        const link = g
            .append("g")
            .selectAll("line")
            .data(edges)
            .join("line")
            .attr("stroke", (d: any) => (d.type === "cites" ? "#1677ff" : "#52c41a"))
            .attr("stroke-width", 1.4)
            .attr("stroke-dasharray", (d: any) => (d.type === "links_to" ? "5,3" : ""))
            .style("opacity", 0.55);
        linkSelRef.current = link as any;

        // 节点
        const node = g
            .append("g")
            .selectAll("g")
            .data(nodes)
            .join("g")
            .style("cursor", "pointer")
            .call(
                d3
                    .drag<SVGGElement, any>()
                    .on("start", (e, d: any) => {
                        if (!e.active) sim.alphaTarget(0.3).restart();
                        d.fx = d.x; d.fy = d.y;
                    })
                    .on("drag", (e, d: any) => { d.fx = e.x; d.fy = e.y; })
                    .on("end", (e, d: any) => {
                        if (!e.active) sim.alphaTarget(0);
                        d.fx = null; d.fy = null;
                    }) as any,
            );

        node
            .append("circle")
            .attr("r", (d: any) => 5 + Math.sqrt((degrees.out.get(d.id) || 0) + (degrees.ind.get(d.id) || 0)) * 2.4)
            .attr("fill", (d: any) => KIND_COLOR[d.source_kind] || "#999")
            .attr("stroke", "#fff")
            .attr("stroke-width", 2);

        node
            .append("text")
            .text((d: any) => (d.title || d.filename).slice(0, 10))
            .attr("x", 12)
            .attr("y", 4)
            .attr("font-size", 10)
            .attr("fill", "#333")
            .style("pointer-events", "none");

        node.append("title").text((d: any) => d.title || d.filename);

        node
            .on("mouseover", (event: any, d: any) => {
                setHovered({
                    id: d.id,
                    title: d.title || d.filename,
                    source_kind: d.source_kind,
                    outDeg: degrees.out.get(d.id) || 0,
                    inDeg: degrees.ind.get(d.id) || 0,
                    x: event.clientX,
                    y: event.clientY,
                });
            })
            .on("mouseout", () => setHovered(null))
            .on("click", (event: any, d: any) => {
                event.stopPropagation();
                setFocusId((cur) => (cur === d.id ? null : d.id));
            });

        nodeSelRef.current = node as any;

        svg.on("click", () => setFocusId(null));

        sim.on("tick", () => {
            link
                .attr("x1", (d: any) => d.source.x)
                .attr("y1", (d: any) => d.source.y)
                .attr("x2", (d: any) => d.target.x)
                .attr("y2", (d: any) => d.target.y);
            node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
        });
    };

    const listNodes = useMemo(() => {
        const arr = (data?.nodes || [])
            .map((n) => ({
                ...n,
                deg: (degrees.out.get(n.id) || 0) + (degrees.ind.get(n.id) || 0),
            }))
            .sort((a, b) => b.deg - a.deg);
        if (!listSearch.trim()) return arr;
        const kw = listSearch.toLowerCase();
        return arr.filter((n) => (n.title || n.filename).toLowerCase().includes(kw));
    }, [data, degrees, listSearch]);

    return (
        <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
                <h1 className="page-title" style={{ margin: 0 }}>
                    知识图谱
                    {focusId && (
                        <Tag color="purple" style={{ marginLeft: 8 }}>
                            聚焦中 · <a onClick={() => setFocusId(null)}>清除</a>
                        </Tag>
                    )}
                </h1>
                <Button onClick={handleRebuild} loading={loading}>重建图谱</Button>
            </div>

            <Row gutter={16} style={{ marginBottom: 16 }}>
                <Col span={6}><Card size="small"><Statistic title="节点" value={data?.stats?.node_count ?? 0} /></Card></Col>
                <Col span={6}><Card size="small"><Statistic title="边" value={data?.stats?.edge_count ?? 0} /></Card></Col>
                <Col span={6}><Card size="small"><Statistic title="Wiki" value={data?.stats?.wiki_nodes ?? 0} valueStyle={{ color: KIND_COLOR.wiki }} /></Card></Col>
                <Col span={6}><Card size="small"><Statistic title="原始文档" value={data?.stats?.raw_nodes ?? 0} valueStyle={{ color: KIND_COLOR.raw }} /></Card></Col>
            </Row>

            <div style={{ display: "flex", gap: 16 }}>
                {/* 筛选 + 图例 */}
                <Card size="small" style={{ width: 200, alignSelf: "flex-start" }}>
                    <div style={{ marginBottom: 12 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>节点类型</Text>
                        <div style={{ marginTop: 6 }}>
                            {(["wiki", "raw", "asset"] as const).map((k) => (
                                <Checkbox
                                    key={k}
                                    checked={filter[k]}
                                    onChange={(e) => setFilter({ ...filter, [k]: e.target.checked })}
                                >
                                    <span style={{ color: KIND_COLOR[k] }}>●</span> {k}
                                </Checkbox>
                            ))}
                        </div>
                    </div>
                    <div style={{ marginBottom: 12 }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>引用类型</Text>
                        <div style={{ marginTop: 6 }}>
                            <Checkbox checked={filter.cites} onChange={(e) => setFilter({ ...filter, cites: e.target.checked })}>
                                <span style={{ color: "#1677ff" }}>━</span> cites
                            </Checkbox>
                            <Checkbox checked={filter.links_to} onChange={(e) => setFilter({ ...filter, links_to: e.target.checked })}>
                                <span style={{ color: "#52c41a" }}>┄┄</span> links_to
                            </Checkbox>
                        </div>
                    </div>
                    <Text type="secondary" style={{ fontSize: 11 }}>
                        点击节点聚焦邻居，再点取消；空白处取消聚焦。
                    </Text>
                </Card>

                {/* 图谱画布 */}
                <Card size="small" style={{ flex: 1, minWidth: 0 }} bodyStyle={{ padding: 0 }}>
                    <div ref={containerRef} style={{ position: "relative" }}>
                        {loading ? (
                            <div style={{ textAlign: "center", padding: 100 }}><Spin size="large" /></div>
                        ) : (
                            <svg ref={svgRef} style={{ width: "100%", height: 520, display: "block" }} />
                        )}
                        {hovered && (
                            <div
                                className="graph-tooltip"
                                style={{ position: "fixed", left: hovered.x + 14, top: hovered.y + 14 }}
                            >
                                <div className="tt-title">{hovered.title}</div>
                                <div className="tt-meta">
                                    {hovered.source_kind} · 出 {hovered.outDeg} · 入 {hovered.inDeg}
                                </div>
                            </div>
                        )}
                    </div>
                </Card>
            </div>

            {/* 节点列表 */}
            <Card size="small" title={`节点列表（${data?.nodes?.length ?? 0}）`} style={{ marginTop: 16 }}>
                <Input.Search
                    placeholder="搜索节点"
                    allowClear
                    value={listSearch}
                    onChange={(e) => setListSearch(e.target.value)}
                    style={{ width: 300, marginBottom: 12 }}
                />
                <div style={{ maxHeight: 260, overflow: "auto" }}>
                    {listNodes.length === 0 ? (
                        <Empty description="暂无节点" />
                    ) : (
                        listNodes.map((n) => (
                            <Link
                                key={n.id}
                                to={`/documents/${n.id}`}
                                style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", borderBottom: "1px solid #f5f5f5" }}
                            >
                                <span
                                    style={{
                                        width: 8, height: 8, borderRadius: "50%", display: "inline-block",
                                        background: KIND_COLOR[n.source_kind] || "#999",
                                    }}
                                />
                                <Text style={{ flex: 1 }}>{n.title || n.filename}</Text>
                                <Text type="secondary" style={{ fontSize: 11 }}>{n.source_kind}</Text>
                                <Tag bordered={false} style={{ fontSize: 11 }}>度 {n.deg}</Tag>
                                {n.status && n.status !== "ready" && (
                                    <Text type="secondary" style={{ fontSize: 11 }}>{STATUS_LABEL[n.status] || n.status}</Text>
                                )}
                            </Link>
                        ))
                    )}
                </div>
            </Card>
        </div>
    );
}
