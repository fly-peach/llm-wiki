import type {
    Document,
    GraphData,
    ReferencesData,
    SearchResult,
    UsageStats,
    Workspace,
    TemplateInfo,
} from "./types";

const BASE = "/v1";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
    const r = await fetch(BASE + url, {
        headers: { "Content-Type": "application/json", ...options?.headers },
        ...options,
    });
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return r.json();
}

export interface ListParams {
    source_kind?: string;
    path?: string;
    status?: string;
    entity_type?: string;
    limit?: number;
    offset?: number;
}

export const api = {
    // ── 工作区 ───────────────────────────────────────
    listWorkspaces: () => request<Workspace[]>("/workspaces"),
    createWorkspace: (path: string, name?: string) =>
        request<Workspace>("/workspaces", { method: "POST", body: JSON.stringify({ path, name }) }),
    deleteWorkspace: (id: string) =>
        request<{ status: string }>(`/workspaces/${id}`, { method: "DELETE" }),
    getCurrentWorkspace: () => request<{ ws_id: string }>("/workspaces/current"),
    setCurrentWorkspace: (ws_id: string) =>
        request<{ status: string; ws_id: string }>("/workspaces/current", {
            method: "PUT",
            body: JSON.stringify({ ws_id }),
        }),

    // ── 文档 ─────────────────────────────────────────
    listDocuments: (params?: ListParams) => {
        const q = new URLSearchParams();
        if (params?.source_kind) q.set("source_kind", params.source_kind);
        if (params?.path) q.set("path", params.path);
        if (params?.status) q.set("status", params.status);
        if (params?.entity_type) q.set("entity_type", params.entity_type);
        if (params?.limit) q.set("limit", String(params.limit));
        if (params?.offset) q.set("offset", String(params.offset));
        return request<{ documents: Document[]; total: number }>(`/documents?${q}`);
    },
    getDocument: (id: string) => request<Document>(`/documents/${id}`),
    getDocumentContent: (id: string) =>
        request<{ doc_id: string; content: string; version: number }>(`/documents/${id}/content`),
    createNote: (data: { filename: string; content: string; path?: string; title?: string }) =>
        request<{ status: string; doc_id: string; filename: string }>("/documents/note", {
            method: "POST",
            body: JSON.stringify(data),
        }),
    updateContent: (id: string, content: string, version: number) =>
        request<{ status: string }>(`/documents/${id}/content`, {
            method: "PUT",
            body: JSON.stringify({ content, expected_version: version }),
        }),
    updateMetadata: (id: string, data: Record<string, unknown>) =>
        request<{ status: string }>(`/documents/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    deleteDocument: (id: string) =>
        request<{ status: string }>(`/documents/${id}`, { method: "DELETE" }),
    bulkDelete: (doc_ids: string[]) =>
        request<{ status: string; deleted: number; total: number }>(`/documents/bulk-delete`, {
            method: "POST",
            body: JSON.stringify({ doc_ids }),
        }),
    getReferences: (id: string) => request<ReferencesData>(`/documents/${id}/references`),

    // ── 高亮 ─────────────────────────────────────────
    getHighlights: (id: string) =>
        request<{ doc_id: string; highlights: unknown[]; version: number }>(`/documents/${id}/highlights`),

    // ── 搜索 ─────────────────────────────────────────
    search: (query: string, limit = 20) =>
        request<{ results: SearchResult[]; query: string; total: number }>(
            `/search?query=${encodeURIComponent(query)}&limit=${limit}`,
        ),

    // ── 图谱 ─────────────────────────────────────────
    getGraph: () => request<GraphData>("/graph"),
    rebuildGraph: () =>
        request<{ status: string; citations: number; links: number; errors: number }>(
            "/graph/rebuild",
            { method: "POST" },
        ),

    // ── Schema ───────────────────────────────────────
    getSchema: () => request<{ content: string; path: string }>("/schema"),
    updateSchema: (content: string) =>
        request<{ status: string; path: string }>("/schema", { method: "PUT", body: JSON.stringify({ content }) }),
    getTemplates: () => request<{ types: TemplateInfo[] }>("/schema/templates"),
    getTemplate: (type: string) =>
        fetch(BASE + `/schema/templates/${type}`).then((r) => r.json()),

    // ── 上传/重建 ────────────────────────────────────
    upload: (file: File, path: string) => {
        const fd = new FormData();
        fd.append("file", file);
        fd.append("path", path);
        return fetch(BASE + "/upload", { method: "POST", body: fd }).then((r) => r.json());
    },
    reindex: (chunkSize?: number) => {
        const params = new URLSearchParams();
        if (chunkSize && chunkSize !== 512) params.set("chunk_size", String(chunkSize));
        const qs = params.toString();
        return request<{
            status: string; indexed: number; skipped: number; errors: number;
            chunk_size: number; chunks_backfilled: number;
        }>("/reindex" + (qs ? `?${qs}` : ""), { method: "POST" });
    },

    // ── 用量/健康 ────────────────────────────────────
    usage: () => request<UsageStats>("/usage"),
    health: () => request<{ status: string; service: string }>("/health"),
};
