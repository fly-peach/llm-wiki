import { useState, type ReactNode } from "react";
import { Link, Outlet, useLocation, useParams } from "react-router-dom";
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

const ROUTE_LABEL: Record<string, string> = {
    "": "首页",
    documents: "文档",
    search: "搜索",
    graph: "图谱",
    schema: "规范",
    workspaces: "工作区",
};

const COLLAPSE_KEY = "llm-sider-collapsed";

export default function Layout() {
    const loc = useLocation();
    const { wsId = "" } = useParams<{ wsId: string }>();
    const { workspaces, current, switchTo } = useWorkspace();
    const [collapsed, setCollapsed] = useState(
        () => localStorage.getItem(COLLAPSE_KEY) === "1",
    );

    const base = `/w/${wsId}`;
    const page = loc.pathname.split("/")[3] || ""; // /w/{wsId}/{page}

    const NAV = [
        { to: base, label: "首页", icon: <DashboardOutlined /> },
        { to: `${base}/documents`, label: "文档", icon: <FileTextOutlined /> },
        { to: `${base}/search`, label: "搜索", icon: <SearchOutlined /> },
        { to: `${base}/graph`, label: "图谱", icon: <ApartmentOutlined /> },
        { to: `${base}/schema`, label: "规范", icon: <SettingOutlined /> },
        { to: "/workspaces", label: "工作区", icon: <FolderOpenOutlined /> },
    ];

    const selected = page === "" ? base : `${base}/${page}`;
    const wsName = workspaces.find((w) => w.id === current)?.name;

    const toggle = () => {
        const c = !collapsed;
        setCollapsed(c);
        localStorage.setItem(COLLAPSE_KEY, c ? "1" : "0");
    };

    // 面包屑
    const crumbs: { title: ReactNode }[] = [{ title: <Link to={base}>首页</Link> }];
    if (page && ROUTE_LABEL[page]) crumbs.push({ title: ROUTE_LABEL[page] });
    if (page === "documents" && loc.pathname.split("/")[4]) crumbs.push({ title: "详情" });

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
                    {wsName && wsName !== "LLM Wiki" && (
                        <span style={{ marginLeft: "auto", color: "#999", fontSize: 12 }}>
                            📁 {wsName}
                        </span>
                    )}
                </Header>
                <Content style={{ padding: 24, background: "var(--llm-bg)" }}>
                    <Outlet />
                </Content>
            </AntLayout>
        </AntLayout>
    );
}
