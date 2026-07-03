import { useMemo, useState } from "react";
import { Tree, Input, type TreeDataNode } from "antd";
import { useNavigate } from "react-router-dom";
import type { Document } from "../lib/types";
import { KIND_COLOR } from "../lib/format";

interface Props {
    docs: Document[];
    selectedDir: string;
    onDirSelect: (dir: string) => void;
}

interface DirNode {
    key: string;
    title: string;
    children: DirNode[];
    isLeaf?: boolean;
    docId?: string;
    kind?: string;
}

function buildTree(docs: Document[]): DirNode[] {
    const root: DirNode = { key: "", title: "", children: [] };
    const dirMap = new Map<string, DirNode>();

    const ensureDir = (path: string, title: string): DirNode => {
        if (dirMap.has(path)) return dirMap.get(path)!;
        const node: DirNode = { key: path, title, children: [] };
        dirMap.set(path, node);
        return node;
    };

    for (const d of docs) {
        const parts = d.relative_path.split("/").filter(Boolean);
        if (parts.length === 0) continue;
        const kind = parts[0];
        let cur = ensureDir(kind, kind);
        let curPath = kind;
        for (let i = 1; i < parts.length - 1; i++) {
            curPath += "/" + parts[i];
            const next = ensureDir(curPath, parts[i]);
            if (!cur.children.includes(next)) cur.children.push(next);
            cur = next;
        }
        cur.children.push({
            key: "doc:" + d.id,
            title: d.title || d.filename,
            isLeaf: true,
            docId: d.id,
            kind: d.source_kind,
            children: [],
        });
    }

    const sortNode = (n: DirNode) => {
        n.children.sort((a, b) => {
            if (!!a.isLeaf !== !!b.isLeaf) return a.isLeaf ? 1 : -1;
            return a.title.localeCompare(b.title, "zh");
        });
        n.children.forEach(sortNode);
    };
    root.children.forEach(sortNode);
    return root.children;
}

const KIND_DIR_LABEL: Record<string, string> = {
    wiki: "📖 Wiki",
    raw: "📄 原始文档",
    asset: "🎨 资产",
};

export default function FileTree({ docs, selectedDir, onDirSelect }: Props) {
    const nav = useNavigate();
    const [search, setSearch] = useState("");

    const treeData = useMemo(() => {
        const dirs = buildTree(docs);
        const toAntd = (nodes: DirNode[]): TreeDataNode[] =>
            nodes.map((n) => ({
                key: n.key,
                title: n.isLeaf ? (
                    <span>
                        <span
                            style={{
                                display: "inline-block",
                                width: 6,
                                height: 6,
                                borderRadius: "50%",
                                background: KIND_COLOR[n.kind || ""] || "#999",
                                marginRight: 6,
                            }}
                        />
                        {n.title}
                    </span>
                ) : (
                    <span>{KIND_DIR_LABEL[n.key.split("/")[0]] || n.title} <span style={{ color: "#999", fontSize: 11 }}>{n.key.split("/")[0] === n.key ? "" : n.title}</span></span>
                ),
                isLeaf: n.isLeaf,
                children: n.isLeaf ? undefined : toAntd(n.children),
            }));
        return toAntd(dirs);
    }, [docs]);

    const filtered = useMemo(() => {
        if (!search.trim()) return treeData;
        const kw = search.toLowerCase();
        const match = (nodes: TreeDataNode[]): TreeDataNode[] => {
            const res: TreeDataNode[] = [];
            for (const n of nodes) {
                const title = String(n.title).toLowerCase();
                const children = n.children ? match(n.children) : [];
                if (title.includes(kw) || children.length) {
                    res.push({ ...n, children: n.children ? children : undefined });
                }
            }
            return res;
        };
        return match(treeData);
    }, [treeData, search]);

    const defaultExpanded = useMemo(
        () => ["wiki", "raw", "asset"].filter((k) => docs.some((d) => d.relative_path.startsWith(k + "/"))),
        [docs],
    );

    return (
        <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
            <Input.Search
                size="small"
                placeholder="过滤文件树"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ marginBottom: 8 }}
                allowClear
            />
            <div style={{ flex: 1, overflow: "auto" }}>
                <Tree
                    treeData={filtered}
                    defaultExpandedKeys={defaultExpanded}
                    selectedKeys={selectedDir ? [selectedDir] : []}
                    showLine={{ showLeafIcon: false }}
                    onSelect={(keys) => {
                        const key = keys[0] as string;
                        if (!key) {
                            onDirSelect("");
                            return;
                        }
                        if (key.startsWith("doc:")) {
                            nav(`/documents/${key.slice(4)}`);
                            return;
                        }
                        onDirSelect(key === selectedDir ? "" : key);
                    }}
                />
            </div>
        </div>
    );
}
