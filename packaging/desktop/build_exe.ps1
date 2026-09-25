# Windows 打包 EXE（在 Windows 上运行）
# 前置: Python 3.11+, Node.js 18+
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $Root

Write-Host "==> 构建前端"
Set-Location frontend
npm install
npm run build
Set-Location $Root

Write-Host "==> 复制静态资源到 backend/static"
if (Test-Path backend\static) { Remove-Item -Recurse -Force backend\static }
New-Item -ItemType Directory -Path backend\static | Out-Null
Copy-Item -Recurse frontend\dist\* backend\static\

Write-Host "==> 安装 Python 依赖与 PyInstaller"
python -m pip install -r backend\requirements.txt pyinstaller

Write-Host "==> 打包 EXE"
python -m PyInstaller `
  --noconfirm --clean --onefile --windowed `
  --name "DieCuttingSystem" `
  --paths backend `
  --add-data "backend/app;app" `
  --add-data "backend/static;static" `
  --hidden-import uvicorn.logging `
  --hidden-import uvicorn.loops `
  --hidden-import uvicorn.loops.auto `
  --hidden-import uvicorn.protocols `
  --hidden-import uvicorn.protocols.http `
  --hidden-import uvicorn.protocols.http.auto `
  --hidden-import uvicorn.protocols.websockets.auto `
  --hidden-import sqlalchemy.dialects.sqlite `
  packaging\desktop\launcher.py

Write-Host "完成: dist\DieCuttingSystem.exe"
Write-Host "首次运行会在 EXE 同目录创建 data/ 数据库文件"
