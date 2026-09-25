#!/usr/bin/env bash
# Linux/macOS 打包（生成可执行文件，非 Windows .exe）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

echo "==> 构建前端"
(cd frontend && npm install && npm run build)

echo "==> 复制静态资源"
rm -rf backend/static
mkdir -p backend/static
cp -r frontend/dist/* backend/static/

echo "==> PyInstaller"
pip install -r backend/requirements.txt pyinstaller
pyinstaller --noconfirm --clean --onefile \
  --name DieCuttingSystem \
  --paths backend \
  --add-data "backend/app:app" \
  --add-data "backend/static:static" \
  --hidden-import uvicorn.logging \
  --hidden-import uvicorn.loops.auto \
  --hidden-import uvicorn.protocols.http.auto \
  --hidden-import sqlalchemy.dialects.sqlite \
  packaging/desktop/launcher.py

echo "完成: dist/DieCuttingSystem"
