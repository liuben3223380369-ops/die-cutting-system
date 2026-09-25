"""模切流程系统桌面启动器 — PyInstaller 打包入口"""
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


def meipass() -> Path | None:
    p = getattr(sys, "_MEIPASS", None)
    return Path(p) if p else None


def ensure_paths() -> Path:
    root = app_root()
    # 开发：backend 在源码树；打包：模块在 _MEIPASS
    backend = root / "backend"
    if backend.exists():
        sys.path.insert(0, str(backend))
    mp = meipass()
    if mp:
        sys.path.insert(0, str(mp))
        static = mp / "static"
        if static.exists():
            os.environ["STATIC_DIR"] = str(static)
    else:
        static = root / "backend" / "static"
        if static.exists():
            os.environ["STATIC_DIR"] = str(static)

    data = root / "data"
    data.mkdir(exist_ok=True)
    os.environ.setdefault(
        "DATABASE_URL",
        f"sqlite+aiosqlite:///{(data / 'die_cutting.db').as_posix()}",
    )
    os.environ.setdefault("APP_ENV", "production")
    os.chdir(root)
    return root


def run_server() -> None:
    import uvicorn
    from app.main import app

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


def main() -> None:
    ensure_paths()
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    for _ in range(40):
        time.sleep(0.25)
        try:
            import urllib.request
            urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=1)
            break
        except Exception:
            continue
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
