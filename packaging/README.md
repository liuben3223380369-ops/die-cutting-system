# 打包说明

| 目标 | 方式 | 产出 |
|------|------|------|
| Windows EXE | `packaging/desktop/build_exe.ps1` | `dist/DieCuttingSystem.exe` |
| Linux 可执行 | `packaging/desktop/build_exe.sh` | `dist/DieCuttingSystem` |
| Android APK | 见 `packaging/android/README.md` | Android Studio 生成 APK |

## EXE 说明

- 单文件启动：内置 FastAPI + 静态前端，浏览器自动打开 `http://127.0.0.1:8000`
- 数据目录：EXE 旁 `data/die_cutting.db`
- **必须在 Windows 本机**运行 `build_exe.ps1`（本仓库服务器环境无法交叉编译 Windows GUI EXE）

## APK 说明

- 前端 WebView 壳，后端需独立运行
- 需本机 Android Studio 完成签名与安装包生成
