import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api } from "./api";
import type { Workspace } from "./types";

interface WorkspaceCtxValue {
    workspaces: Workspace[];
    /** 当前工作区 ID — 来自 URL /w/:wsId，未在 ws 路由下时为空串 */
    current: string;
    loaded: boolean;
    switchTo: (wsId: string) => Promise<void>;
    refresh: () => Promise<void>;
}

const WorkspaceCtx = createContext<WorkspaceCtxValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
    const loc = useLocation();
    const nav = useNavigate();
    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [loaded, setLoaded] = useState(false);

    // current 来自 URL: /w/:wsId/...
    const current = useMemo(() => {
        const m = loc.pathname.match(/^\/w\/([^/]+)/);
        return m ? m[1] : "";
    }, [loc.pathname]);

    const refresh = async () => {
        const ws = await api.listWorkspaces().catch(() => [] as Workspace[]);
        setWorkspaces(ws);
        setLoaded(true);
    };

    useEffect(() => {
        (async () => {
            await refresh();
        })();
    }, []);

    // URL 携带 wsId 时同步到后端全局 current，保证后端 API 用对工作区
    useEffect(() => {
        if (current) {
            api.setCurrentWorkspace(current).catch(() => {});
        }
    }, [current]);

    const switchTo = async (wsId: string) => {
        await api.setCurrentWorkspace(wsId);
        nav(`/w/${wsId}`);
    };

    return (
        <WorkspaceCtx.Provider value={{ workspaces, current, loaded, switchTo, refresh }}>
            {children}
        </WorkspaceCtx.Provider>
    );
}

export function useWorkspace(): WorkspaceCtxValue {
    const ctx = useContext(WorkspaceCtx);
    if (!ctx) throw new Error("useWorkspace must be used within WorkspaceProvider");
    return ctx;
}
