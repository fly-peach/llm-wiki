// 格式化与展示工具函数

/** 文件大小人性化: 3.2 KB / 2.1 MB */
export function formatBytes(bytes?: number | null): string {
    if (!bytes || bytes <= 0) return "—";
    const units = ["B", "KB", "MB", "GB"];
    let v = bytes;
    let i = 0;
    while (v >= 1024 && i < units.length - 1) {
        v /= 1024;
        i++;
    }
    return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1)} ${units[i]}`;
}

/** 相对时间: 2小时前 / 昨天 */
export function relativeTime(iso?: string | null): string {
    if (!iso) return "—";
    const t = new Date(iso).getTime();
    if (isNaN(t)) return iso;
    const diff = Date.now() - t;
    const sec = Math.floor(diff / 1000);
    if (sec < 60) return "刚刚";
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min} 分钟前`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr} 小时前`;
    const day = Math.floor(hr / 24);
    if (day === 1) return "昨天";
    if (day < 30) return `${day} 天前`;
    const mon = Math.floor(day / 30);
    if (mon < 12) return `${mon} 个月前`;
    return `${Math.floor(mon / 12)} 年前`;
}

/** 绝对时间: 2026-07-03 14:30 */
export function formatDate(iso?: string | null): string {
    if (!iso) return "—";
    const t = new Date(iso);
    if (isNaN(t.getTime())) return iso;
    return t.toLocaleString("zh-CN", {
        year: "numeric", month: "2-digit", day: "2-digit",
        hour: "2-digit", minute: "2-digit",
    });
}

/** 从 relative_path 提取目录段: "wiki/entities/attn.md" → ["wiki","entities"] */
export function pathSegments(relativePath?: string): string[] {
    if (!relativePath) return [];
    return relativePath.split("/").filter(Boolean).slice(0, -1);
}

/** 文件名(去扩展名) */
export function stem(filename?: string | null): string {
    if (!filename) return "";
    const i = filename.lastIndexOf(".");
    return i > 0 ? filename.slice(0, i) : filename;
}

/** 字数估算(中文字符 + 英文词) */
export function wordCount(content?: string | null): number {
    if (!content) return 0;
    const cjk = (content.match(/[一-龥]/g) || []).length;
    const en = (content.replace(/[一-龥]/g, " ").trim().match(/\S+/g) || []).length;
    return cjk + en;
}

/** 三类语义色 */
export const KIND_COLOR: Record<string, string> = {
    wiki: "#52c41a",
    raw: "#1677ff",
    asset: "#fa8c16",
};

export const KIND_LABEL: Record<string, string> = {
    wiki: "Wiki",
    raw: "原始文档",
    asset: "资产",
};

/** 状态色与标签 */
export const STATUS_COLOR: Record<string, string> = {
    ready: "#52c41a",
    pending: "#8c8c8c",
    processing: "#1677ff",
    failed: "#ff4d4f",
    stale: "#faad14",
    deleted: "#d9d9d9",
};

export const STATUS_LABEL: Record<string, string> = {
    ready: "就绪",
    pending: "待处理",
    processing: "处理中",
    failed: "失败",
    stale: "过期",
    deleted: "已删除",
};

/** 关键词高亮: 在文本中标记匹配片段(返回带 <mark> 的 HTML 安全片段) */
export function highlightText(text: string, query: string): string {
    if (!query.trim()) return escapeHtml(text);
    const terms = query.trim().split(/\s+/).filter(Boolean).map(escapeRegExp);
    if (terms.length === 0) return escapeHtml(text);
    const re = new RegExp(`(${terms.join("|")})`, "gi");
    return escapeHtml(text).replace(re, '<mark class="search-hit">$1</mark>');
}

function escapeRegExp(s: string): string {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function escapeHtml(s: string): string {
    return s
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

/** 截取摘要 */
export function truncate(s: string, n = 300): string {
    if (!s) return "";
    return s.length > n ? s.slice(0, n) + "…" : s;
}
