import { Routes, Route, Navigate } from "react-router-dom";
import { Spin } from "antd";
import Layout from "./components/Layout";
import Onboarding from "./components/Onboarding";
import { useWorkspace } from "./lib/workspace-context";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import DocumentView from "./pages/DocumentView";
import GraphView from "./pages/GraphView";
import SchemaEditor from "./pages/SchemaEditor";
import SearchPage from "./pages/SearchPage";
import WorkspaceManager from "./pages/WorkspaceManager";

export default function App() {
    const { loaded, workspaces } = useWorkspace();

    // 首启：未加载完成时显示加载态
    if (!loaded) {
        return (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh" }}>
                <Spin size="large" />
            </div>
        );
    }

    // 没有任何工作区 → 强制引导创建，不进入主界面
    if (workspaces.length === 0) {
        return <Onboarding />;
    }

    return (
        <Routes>
            <Route path="/workspaces" element={<WorkspaceManager />} />
            <Route path="/w/:wsId" element={<Layout />}>
                <Route index element={<Dashboard />} />
                <Route path="documents" element={<Documents />} />
                <Route path="documents/:id" element={<DocumentView />} />
                <Route path="graph" element={<GraphView />} />
                <Route path="schema" element={<SchemaEditor />} />
                <Route path="search" element={<SearchPage />} />
            </Route>
            <Route path="/" element={<Navigate to={`/w/${workspaces[0].id}`} replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
}
