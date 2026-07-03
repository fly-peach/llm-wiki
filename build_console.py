#!/usr/bin/env python
"""
构建前端并复制到后端静态目录（参考 DataApp1.0 backend/build_console.py）

用法（项目根目录下）:
    python build_console.py              # 构建前端 → 复制到 api/static/
    python build_console.py --install    # 重装依赖 + 构建 + 复制
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).absolute().parent
WEB_DIR = ROOT / "web"
STATIC_DIR = ROOT / "api" / "static"


def check_deps() -> bool:
    if (WEB_DIR / "node_modules").exists():
        return True
    print("\n[1/3] 安装依赖...")
    try:
        subprocess.run(["npm", "install"], cwd=str(WEB_DIR), check=True, shell=True)
        print("  OK")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  FAIL: {e}")
        return False


def do_build() -> bool:
    print("\n[2/3] 构建前端...")
    try:
        subprocess.run(["npm", "run", "build"], cwd=str(WEB_DIR), check=True, shell=True)
        print("  OK")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"  FAIL: {e}")
        return False


def do_copy() -> bool:
    dist = WEB_DIR / "dist"
    if not dist.exists():
        print(f"  FAIL: dist/ 不存在: {dist}")
        return False
    print(f"\n[3/3] 复制 dist/ → {STATIC_DIR} ...")
    if STATIC_DIR.exists():
        shutil.rmtree(STATIC_DIR, ignore_errors=True)
    shutil.copytree(dist, STATIC_DIR)
    print(f"  OK → {STATIC_DIR}")
    return True


def main():
    parser = argparse.ArgumentParser(description="LLM Wiki — 前端构建 & 挂载")
    parser.add_argument("--install", action="store_true", help="重新安装 npm 依赖")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    if args.install:
        nm = WEB_DIR / "node_modules"
        if nm.exists():
            shutil.rmtree(nm, ignore_errors=True)
            print("[install] 已清理 node_modules")

    print("=" * 50)
    print("  LLM Wiki — 前端构建 & 挂载")
    print("=" * 50)

    if not check_deps():
        sys.exit(1)
    if not do_build():
        sys.exit(1)
    if not do_copy():
        sys.exit(1)

    print("\n" + "=" * 50)
    print("  构建完成!")
    print(f"  启动服务: python llmwiki.py --prod")
    print("=" * 50)


if __name__ == "__main__":
    main()
