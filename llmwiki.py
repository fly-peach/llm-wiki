#!/usr/bin/env python
"""LLM Wiki — 服务启动 CLI

用法（项目根目录下）:
    python llmwiki.py                   # 开发模式: API + MCP 配置
    python llmwiki.py --prod            # 生产模式: API serve 前端 (需先 python build_console.py)
    python llmwiki.py --port 9000       # 指定端口

生产流程:
    python build_console.py             # 构建前端 → api/static/
    python llmwiki.py --prod            # 启动，直接访问 :8000
"""

from __future__ import annotations

import argparse
import asyncio
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).absolute().parent
API_DIR = ROOT / "api"


def _get_lan_ip() -> str:
    """获取本机局域网 IPv4 地址（优先取非回环的私网地址）。"""
    try:
        # 方法 1：连接到外部地址获取实际使用的网卡 IP（不实际发包）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        # 不需要真正连通，只是获取路由表决定的本地地址
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass

    # 方法 2：回退到遍历所有网卡
    try:
        for name, addr in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = addr[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass

    return ""


def set_env(prod: bool = False) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(API_DIR.resolve())
    if prod:
        env["LLMWIKI_PROD"] = "true"
    return env


async def start_api(port: int = 8000, prod: bool = False):
    import uvicorn
    sys.path.insert(0, str(API_DIR))
    config = uvicorn.Config(
        "main:app", host="0.0.0.0", port=port,
        reload=not prod, log_level="info",
    )
    await uvicorn.Server(config).serve()


def show_mcp(port: int, lan_ip: str = ""):
    print()
    print("── MCP Server（fastapi-mcp，同进程 HTTP）──")
    print(f"  本机:   http://localhost:{port}/mcp")
    if lan_ip:
        print(f"  局域网: http://{lan_ip}:{port}/mcp")
    print(f"  客户端: url = http://localhost:{port}/mcp")
    print("  （无需单独起 MCP 进程，复用 REST 接口）")
    print()


async def main():
    p = argparse.ArgumentParser(description="LLM Wiki")
    p.add_argument("--prod", action="store_true", help="生产模式")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()

    lan_ip = _get_lan_ip()

    if args.prod:
        print("=" * 55)
        print("  LLM Wiki — Production")
        print(f"  本机:   http://localhost:{args.port}")
        if lan_ip:
            print(f"  局域网: http://{lan_ip}:{args.port}")
        print("=" * 55)
        show_mcp(args.port, lan_ip)
        await start_api(args.port, prod=True)
        return

    print("=" * 55)
    print("  LLM Wiki — Development")
    print(f"  API:     http://localhost:{args.port}")
    if lan_ip:
        print(f"  局域网:  http://{lan_ip}:{args.port}")
    print(f"  Swagger: http://localhost:{args.port}/docs")
    print(f"  前端:     cd web && npm run dev")
    print("=" * 55)
    show_mcp(args.port, lan_ip)
    await start_api(args.port)


if __name__ == "__main__":
    asyncio.run(main())
