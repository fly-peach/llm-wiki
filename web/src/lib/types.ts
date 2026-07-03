// 后端数据模型 TypeScript 类型定义

export type SourceKind = "raw" | "wiki" | "asset";
export type DocStatus = "pending" | "processing" | "ready" | "failed" | "deleted" | string;

export interface Highlight {
    id?: string;
    text?: string;
    start?: number;
    end?: number;
    page?: number;
    note?: string;
    color?: string;
    [key: string]: unknown;
}

export interface Document {
    id: string;
    filename: string;
    title: string | null;
    path: string;
    relative_path: string;
    source_kind: SourceKind;
    file_type: string;
    file_size: number;
    document_number: number | null;
    status: DocStatus;
    page_count: number | null;
    content: string;
    tags: string; // JSON 字符串
    date: string | null;
    metadata: string; // JSON 字符串
    error_message: string | null;
    version: number;
    parser: string | null;
    content_hash: string | null;
    mtime_ns: number | null;
    last_indexed_at: string | null;
    stale_since: string | null;
    highlights: string; // JSON 字符串
    entity_type: string | null;
    domain: string | null;
    created_at: string;
    updated_at: string;
}

export interface SearchResult {
    doc_id: string;
    filename: string;
    title: string;
    source_kind: SourceKind;
    chunk_index: number | null;
    chunk_content: string;
    header_breadcrumb: string;
    token_count: number;
}

export interface GraphNode {
    id: string;
    title: string;
    filename: string;
    source_kind: SourceKind;
    file_type: string;
    path: string;
    status: string;
}

export interface GraphEdge {
    source: string;
    target: string;
    type: "cites" | "links_to";
    page: number | null;
}

export interface GraphData {
    nodes: GraphNode[];
    edges: GraphEdge[];
    stats: {
        node_count: number;
        edge_count: number;
        wiki_nodes: number;
        raw_nodes: number;
    };
}

export interface ReferenceItem {
    id: string;
    title: string;
    filename: string;
    source_kind: SourceKind;
    relative_path: string;
    type: "cites" | "links_to";
    page: number | null;
}

export interface ReferencesData {
    outgoing: ReferenceItem[];
    incoming: ReferenceItem[];
}

export interface Workspace {
    id: string;
    name: string;
    path: string;
    kind: string;
    created_at: string;
}

export interface UsageStats {
    documents: number;
    wiki_pages: number;
    raw_files: number;
    assets: number;
    by_status: Record<string, number>;
    by_entity: { entity_type: string; count: number }[];
    recent: {
        id: string;
        title: string;
        filename: string;
        source_kind: SourceKind;
        status: string;
        updated_at: string;
    }[];
}

export interface TemplateInfo {
    key: string;
    label: string;
    folder: string;
}

// ── JSON 字符串字段解析工具 ─────────────────────────

export function parseJsonArray(s?: string | null): unknown[] {
    if (!s) return [];
    try {
        const v = JSON.parse(s);
        return Array.isArray(v) ? v : [];
    } catch {
        return [];
    }
}

export function parseJsonObj(s?: string | null): Record<string, unknown> {
    if (!s) return {};
    try {
        const v = JSON.parse(s);
        return typeof v === "object" && v ? (v as Record<string, unknown>) : {};
    } catch {
        return {};
    }
}

export function parseTags(s?: string | null): string[] {
    return parseJsonArray(s).filter((x): x is string => typeof x === "string");
}

export function parseHighlights(s?: string | null): Highlight[] {
    return parseJsonArray(s).filter((x): x is Record<string, unknown> => typeof x === "object" && x !== null) as unknown as Highlight[];
}

export function parseMetadata(s?: string | null): Record<string, unknown> {
    return parseJsonObj(s);
}
