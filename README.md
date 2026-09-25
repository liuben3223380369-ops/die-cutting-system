# 模切流程系统（完整交付）

从《模切流程系统-初版开发清单》落地的 **完整可运行工程**：计划 → 开发 → 部署 → 打包说明。

## 仓库内容

| 目录 | 说明 |
|------|------|
| `backend/` | FastAPI 后端（采购/库存/工程/MRP/生产/质量/成本/期间） |
| `frontend/` | Vue3 + TypeScript 前端全部业务页 |
| `docs/` | 项目计划、文件清单、迁移说明 |
| `packaging/` | Windows EXE / Android APK 本机构建脚本 |
| `docker-compose.yml` | 一键容器部署 |

详见 [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) 与 [docs/FILE_MANIFEST.txt](docs/FILE_MANIFEST.txt)。

## 快速启动

```bash
# Docker
docker compose up --build

# 或本地
cd backend && pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
# 另开终端
cd frontend && npm install && npm run dev
```

演示数据：`cd backend && python scripts/seed_demo_data.py`

## 打包 EXE / APK

本仓库是 **Web 制造系统**，安装包需在目标系统上构建：

- **Windows EXE**：在 Windows 执行 `packaging/desktop/build_exe.ps1` → 生成 `dist/DieCuttingSystem.exe`
- **Android APK**：按 `packaging/android/README.md` 用 Android Studio 出包

GitHub Actions 可后续接入 `windows-latest` / Android 构建机自动产物。

## 业务闭环

主数据 → 工程发布 → 销售/MRP → 采购入库/IQC → 工单领料报工入库 → 质量成本 → 关账

## License

私有/内部使用，以仓库所有者为准。
