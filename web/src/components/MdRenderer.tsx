import { memo, useMemo, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
import { useNavigate, useParams } from "react-router-dom";
import MermaidBlock from "./MermaidBlock";

function slug(s: string): string {
    return (
        s
            .toLowerCase()
            .replace(/[^\w一-龥 ]/g, "")
            .trim()
            .replace(/\s+/g, "-") || "section"
    );
}

export function extractText(children: ReactNode): string {
    if (typeof children === "string" || typeof children === "number") return String(children);
    if (Array.isArray(children)) return children.map(extractText).join("");
    if (children && typeof children === "object" && "props" in (children as any)) {
        return extractText((children as any).props.children);
    }
    return "";
}

interface Props {
    content: string;
    wikiLinkMap?: Map<string, string>;
    sourceMap?: Map<string, string>;
}

function MdRendererBase({ content, wikiLinkMap, sourceMap }: Props) {
    const nav = useNavigate();
    const { wsId = "" } = useParams<{ wsId: string }>();

    const components = useMemo(
        () => ({
            h2: ({ children }: any) => <h2 id={slug(extractText(children))}>{children}</h2>,
            h3: ({ children }: any) => <h3 id={slug(extractText(children))}>{children}</h3>,
            a: ({ href, children }: any) => {
                if (!href) return <a>{children}</a>;
                if (href.startsWith("#")) return <a href={href}>{children}</a>;
                if (/^(https?:|mailto:)/.test(href)) {
                    return (
                        <a href={href} target="_blank" rel="noreferrer">
                            {children}
                        </a>
                    );
                }
                const target = href.replace(/^\.?\//, "").toLowerCase();
                const stem = target.replace(/\.md$/i, "");
                const wid = wikiLinkMap?.get(target) || wikiLinkMap?.get(stem) || wikiLinkMap?.get(stem + ".md");
                if (wid) {
                    return (
                        <a className="wiki-link" onClick={() => nav(`/w/${wsId}/documents/${wid}`)}>
                            {children}
                        </a>
                    );
                }
                const sid = sourceMap?.get(target);
                if (sid) {
                    return (
                        <a className="source-link" onClick={() => nav(`/w/${wsId}/documents/${sid}`)}>
                            {children}
                        </a>
                    );
                }
                return <a title="未找到链接目标">{children}</a>;
            },
            pre: ({ children }: any) => {
                const codeEl: any = Array.isArray(children) ? children[0] : children;
                const cls: string = codeEl?.props?.className || "";
                if (cls === "language-mermaid") {
                    return <div className="mermaid-wrap">{codeEl}</div>;
                }
                return <pre>{children}</pre>;
            },
            code: ({ inline, className, children }: any) => {
                if (!inline && className === "language-mermaid") {
                    return <MermaidBlock chart={extractText(children)} />;
                }
                return <code className={className}>{children}</code>;
            },
        }),
        [wikiLinkMap, sourceMap, nav],
    );

    return (
        <div className="wiki-prose">
            <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkMath]}
                rehypePlugins={[rehypeHighlight, rehypeKatex]}
                components={components as any}
            >
                {content || "(暂无内容)"}
            </ReactMarkdown>
        </div>
    );
}

export default memo(MdRendererBase);
