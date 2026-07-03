import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import { WorkspaceProvider } from "./lib/workspace-context";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
        <ConfigProvider
            locale={zhCN}
            theme={{ token: { colorPrimary: "#4f46e5", borderRadius: 6 } }}
        >
            <BrowserRouter>
                <WorkspaceProvider>
                    <App />
                </WorkspaceProvider>
            </BrowserRouter>
        </ConfigProvider>
    </React.StrictMode>
);
