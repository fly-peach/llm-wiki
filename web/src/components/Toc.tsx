import { useEffect, useState } from "react";
import { Typography } from "antd";

const { Text } = Typography;

export interface TocItem {
    level: number;
    text: string;
    id: string;
}

export function slugify(s: string): string {
    return (
        s
            .toLowerCase()
            .replace(/[^\w一-龥 ]/g, "")
            .trim()
            .replace(/\s+/g, "-") || "section"
    );
}

export function extractToc(md: string): TocItem[] {
    const items: TocItem[] = [];
    for (const line of md.split("\n")) {
        const m = line.match(/^(#{2,3})\s+(.+?)\s*#*\s*$/);
        if (!m) continue;
        const level = m[1].length;
        const text = m[2]
            .replace(/\[[^\]]*\]\([^)]*\)/g, "")
            .replace(/\[\^[^\]]*\]/g, "")
            .trim();
        if (!text) continue;
        items.push({ level, text, id: slugify(text) });
    }
    return items;
}

export default function Toc({ md }: { md: string }) {
    const items = extractToc(md);
    const [active, setActive] = useState("");

    useEffect(() => {
        const obs = new IntersectionObserver(
            (entries) => {
                for (const e of entries) {
                    if (e.isIntersecting) setActive((e.target as HTMLElement).id);
                }
            },
            { rootMargin: "-60px 0px -80% 0px" },
        );
        items.forEach((it) => {
            const el = document.getElementById(it.id);
            if (el) obs.observe(el);
        });
        return () => obs.disconnect();
    }, [md]);

    if (items.length === 0) return null;

    return (
        <div>
            <Text type="secondary" style={{ fontSize: 12, fontWeight: 600 }}>
                📑 目录
            </Text>
            <div style={{ marginTop: 8 }}>
                {items.map((it, i) => (
                    <div key={i} style={{ paddingLeft: (it.level - 2) * 12, marginBottom: 4 }}>
                        <a
                            href={`#${it.id}`}
                            onClick={(e) => {
                                e.preventDefault();
                                document.getElementById(it.id)?.scrollIntoView({ behavior: "smooth" });
                            }}
                            style={{
                                fontSize: 13,
                                color: active === it.id ? "var(--llm-indigo)" : "var(--llm-text-2)",
                                fontWeight: active === it.id ? 600 : 400,
                                textDecoration: "none",
                            }}
                        >
                            {it.text}
                        </a>
                    </div>
                ))}
            </div>
        </div>
    );
}
