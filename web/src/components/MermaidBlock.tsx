import { useEffect, useState } from "react";

let mermaidPromise: Promise<typeof import("mermaid")["default"]> | null = null;

function loadMermaid() {
    if (!mermaidPromise) {
        mermaidPromise = import("mermaid").then((m) => {
            const mermaid = m.default;
            mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });
            return mermaid;
        });
    }
    return mermaidPromise;
}

export default function MermaidBlock({ chart }: { chart: string }) {
    const [svg, setSvg] = useState<string>("");
    const [err, setErr] = useState<string>("");

    useEffect(() => {
        let cancelled = false;
        const id = "mermaid-" + Math.random().toString(36).slice(2, 10);
        loadMermaid()
            .then((mermaid) => mermaid.render(id, chart))
            .then((res: any) => {
                if (!cancelled) {
                    setSvg(res.svg);
                    setErr("");
                }
            })
            .catch((e: any) => {
                if (!cancelled) setErr(String(e?.message || e));
            });
        return () => {
            cancelled = true;
        };
    }, [chart]);

    if (err) {
        return (
            <div className="mermaid-wrap" style={{ color: "#ff4d4f", fontFamily: "monospace", fontSize: 12 }}>
                Mermaid 渲染失败: {err}
                <pre style={{ marginTop: 8 }}>{chart}</pre>
            </div>
        );
    }
    return <div className="mermaid-wrap" dangerouslySetInnerHTML={{ __html: svg }} />;
}
