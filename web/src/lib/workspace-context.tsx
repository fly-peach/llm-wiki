import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "./api";
import type { Workspace } from "./types";

interface WorkspaceCtxValue {
    workspaces: Workspace[];
    current: string;
    loaded: boolean;
    switchTo: (wsId: string) => Promise<void>;
    refresh: () => Promise<void>;
}

const WorkspaceCtx = createContext<WorkspaceCtxValue | null>(null);

export function WorkspaceProvider({ children }: { children: ReactNode }) {
    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [current, setCurrent] = useState("");
    const [loaded, setLoaded] = useState(false);

    const refresh = async () => {
        const ws = await api.listWorkspaces().catch(() => [] as Workspace[]);
        setWorkspaces(ws);
        const cur = await api.getCurrentWorkspace().catch(() => ({ ws_id: "" }));
        setCurrent(cur.ws_id);
    };

    useEffect(() => {
        (async () => {
            await refresh();
            setLoaded(true);
        })();
    }, []);

    const switchTo = async (wsId: string) => {
        await api.setCurrentWorkspace(wsId);
        setCurrent(wsId);
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
