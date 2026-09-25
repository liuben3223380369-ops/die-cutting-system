"""模切流程系统桌面启动器

打包为 EXE 后：启动内置后端，打开浏览器访问本地页面。
构建前请先执行 frontend 构建，并把 dist 复制到 backend/static。
"""
from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def ensure_paths():
    root = app_root()
    # 让 backend 可被导入
    backend = root / "backend"
    if backend.exists():
        sys.path.insert(0, str(backend))
    os.chdir(root)
    data = root / "data"
    data.mkdir(exist_ok=True)
    os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{data / 'die_cutting.db'}")
    static = root / "backend" / "static"
    if static.exists():
        os.environ.setdefault("STATIC_DIR", str(static))
    return root


def run_server():
    import uvicorn
    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


def main():
    ensure_paths()
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000/")
    print("模切流程系统已启动: http://127.0.0.1:8000/")
    print("关闭本窗口将停止服务。")
    try:
        while t.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
