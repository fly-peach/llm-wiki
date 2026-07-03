import { useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { Layout as AntLayout, Menu, Select, Breadcrumb, Button } from "antd";
import {
    DashboardOutlined,
    FileTextOutlined,
    SearchOutlined,
    ApartmentOutlined,
    SettingOutlined,
    FolderOpenOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
} from "@ant-design/icons";
import { useWorkspace } from "../lib/workspace-context";

const { Sider, Content, Header } = AntLayout;

const NAV = [
    { to: "/", label: "首页", icon: <DashboardOutlined /> },
    { to: "/documents", label: "文档", icon: <FileTextOutlined /> },
    { to: "/search", label: "搜索", icon: <SearchOutlined /> },
    { to: "/graph", label: "图谱", icon: <ApartmentOutlined /> },
    { to: "/schema", label: "规范", icon: <SettingOutlined /> },
    { to: "/workspaces", label: "工作区", icon: <FolderOpenOutlined /> },
];

const ROUTE_LABEL: Record<string, string> = {
    "": "首页",
    documents: "文档",
    search: "搜索",
    graph: "图谱",
    schema: "规范",
    workspaces: "工作区",
};

const COLLAPSE_KEY = "llm-sider-collapsed";

export default function Layout({ children }: { children: ReactNode }) {
    const loc = useLocation();
    const { workspaces, current, switchTo } = useWorkspace();
    const [collapsed, setCollapsed] = useState(
        () => localStorage.getItem(COLLAPSE_KEY) === "1",
    );

    const seg = loc.pathname.split("/")[1] || "";
    const selected = "/" + seg;

    const toggle = () => {
        const c = !collapsed;
        setCollapsed(c);
        localStorage.setItem(COLLAPSE_KEY, c ? "1" : "0");
    };

    // 面包屑
    const crumbs: { title: ReactNode }[] = [{ title: <Link to="/">首页</Link> }];
    if (seg && ROUTE_LABEL[seg]) crumbs.push({ title: ROUTE_LABEL[seg] });
    if (seg === "documents" && loc.pathname.split("/")[2]) crumbs.push({ title: "详情" });

    return (
        <AntLayout style={{ minHeight: "100vh" }}>
            <Sider
                theme="dark"
                width={216}
                collapsedWidth={80}
                collapsed={collapsed}
                collapsible
                trigger={null}
            >
                <div
                    style={{
                        height: 56,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#fff",
                        fontSize: collapsed ? 22 : 16,
                        fontWeight: 700,
                        borderBottom: "1px solid rgba(255,255,255,0.08)",
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                    }}
                >
                    {collapsed ? "🧠" : "🧠 LLM Wiki"}
                </div>

                {!collapsed && (
                    <div style={{ padding: "12px 12px" }}>
                        <Select
                            showSearch
                            placeholder="选择工作区"
                            value={current || undefined}
                            onChange={(v: string) => switchTo(v)}
                            style={{ width: "100%" }}
                            options={workspaces.map((w) => ({ value: w.id, label: `📁 ${w.name}` }))}
                        />
                    </div>
                )}

                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={[selected]}
                    items={NAV.map((n) => ({
                        key: n.to,
                        icon: n.icon,
                        label: <Link to={n.to}>{n.label}</Link>,
                    }))}
                />
            </Sider>

            <AntLayout>
                <Header
                    style={{
                        background: "#fff",
                        padding: "0 16px",
                        borderBottom: "1px solid var(--llm-border)",
                        height: 48,
                        lineHeight: "48px",
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                    }}
                >
                    <Button
                        type="text"
                        icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                        onClick={toggle}
                        title={collapsed ? "展开侧栏" : "收起侧栏"}
                    />
                    <Breadcrumb items={crumbs} />
                </Header>
                <Content style={{ padding: 24, background: "var(--llm-bg)" }}>{children}</Content>
            </AntLayout>
        </AntLayout>
    );
}
