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
import sys
from pathlib import Path

ROOT = Path(__file__).absolute().parent
API_DIR = ROOT / "api"


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


def show_mcp():
    print()
    print("── MCP Server（fastapi-mcp，同进程 HTTP）──")
    print("  端点:   http://localhost:8000/mcp")
    print("  客户端:  url = http://localhost:8000/mcp")
    print("  （无需单独起 MCP 进程，复用 REST 接口）")
    print()


async def main():
    p = argparse.ArgumentParser(description="LLM Wiki")
    p.add_argument("--prod", action="store_true", help="生产模式")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()

    if args.prod:
        print("=" * 50)
        print("  LLM Wiki — Production")
        print(f"  http://localhost:{args.port}")
        print("=" * 50)
        await start_api(args.port, prod=True)
        return

    print("=" * 50)
    print("  LLM Wiki — Development")
    print(f"  API:     http://localhost:{args.port}")
    print(f"  Swagger: http://localhost:{args.port}/docs")
    print(f"  前端:     cd web && npm run dev")
    print("=" * 50)
    show_mcp()
    await start_api(args.port)


if __name__ == "__main__":
    asyncio.run(main())
