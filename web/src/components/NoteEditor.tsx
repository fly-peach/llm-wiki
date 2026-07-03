import { useEffect, type ReactNode } from "react";
import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import Typography from "@tiptap/extension-typography";
import { Markdown } from "tiptap-markdown";
import { Button, Space, Divider } from "antd";
import {
    BoldOutlined,
    ItalicOutlined,
    UnorderedListOutlined,
    OrderedListOutlined,
    MessageOutlined,
    CodeOutlined,
    LinkOutlined,
} from "@ant-design/icons";

interface Props {
    value: string;
    onChange: (md: string) => void;
}

export default function NoteEditor({ value, onChange }: Props) {
    const editor = useEditor({
        extensions: [
            StarterKit,
            Link.configure({ openOnClick: false, HTMLAttributes: { class: "wiki-link" } }),
            Placeholder.configure({
                placeholder: "输入内容… 用 [^1]: 标注引用，[text](page.md) 交叉链接",
            }),
            Typography,
            Markdown.configure({
                html: false,
                breaks: true,
                transformPastedText: true,
                transformCopiedText: true,
            }),
        ],
        content: value,
        onUpdate: ({ editor }) => {
            try {
                const md = (editor.storage as any).markdown?.getMarkdown?.() ?? "";
                onChange(md);
            } catch {
                /* ignore */
            }
        },
    });

    useEffect(() => {
        if (!editor) return;
        try {
            const current = (editor.storage as any).markdown?.getMarkdown?.() ?? "";
            if (value !== current) {
                editor.commands.setContent(value || "");
            }
        } catch {
            editor.commands.setContent(value || "");
        }
    }, [value, editor]);

    if (!editor) return null;

    const btn = (icon: ReactNode, action: () => void, active: boolean, title: string) => (
        <Button size="small" type={active ? "primary" : "text"} icon={icon} onClick={action} title={title} />
    );

    const setLink = () => {
        const url = window.prompt("链接地址（可用 page.md 内链或 https://…）");
        if (url === null) return;
        if (url === "") {
            editor.chain().focus().unsetLink().run();
            return;
        }
        editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
    };

    return (
        <div>
            <Space wrap style={{ marginBottom: 8, padding: 6, background: "#fafafa", borderRadius: 6, border: "1px solid var(--llm-border)" }}>
                {btn(<BoldOutlined />, () => editor.chain().focus().toggleBold().run(), editor.isActive("bold"), "粗体")}
                {btn(<ItalicOutlined />, () => editor.chain().focus().toggleItalic().run(), editor.isActive("italic"), "斜体")}
                <Divider type="vertical" style={{ margin: "0 4px" }} />
                <Button size="small" type={editor.isActive("heading", { level: 1 }) ? "primary" : "text"} onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} title="一级标题">H1</Button>
                <Button size="small" type={editor.isActive("heading", { level: 2 }) ? "primary" : "text"} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} title="二级标题">H2</Button>
                <Button size="small" type={editor.isActive("heading", { level: 3 }) ? "primary" : "text"} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} title="三级标题">H3</Button>
                <Divider type="vertical" style={{ margin: "0 4px" }} />
                {btn(<UnorderedListOutlined />, () => editor.chain().focus().toggleBulletList().run(), editor.isActive("bulletList"), "无序列表")}
                {btn(<OrderedListOutlined />, () => editor.chain().focus().toggleOrderedList().run(), editor.isActive("orderedList"), "有序列表")}
                {btn(<MessageOutlined />, () => editor.chain().focus().toggleBlockquote().run(), editor.isActive("blockquote"), "引用")}
                {btn(<CodeOutlined />, () => editor.chain().focus().toggleCodeBlock().run(), editor.isActive("codeBlock"), "代码块")}
                <Divider type="vertical" style={{ margin: "0 4px" }} />
                {btn(<LinkOutlined />, setLink, editor.isActive("link"), "链接")}
            </Space>
            <div className="wiki-prose">
                <EditorContent editor={editor} />
            </div>
        </div>
    );
}
