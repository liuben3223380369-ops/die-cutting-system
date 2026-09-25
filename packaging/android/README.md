# Android APK 打包说明

本系统是 **Web 应用**。APK 使用 Capacitor 将前端打成 WebView 壳，后端需单独部署（局域网 IP 或公网）。

## 前置条件

- Node.js 18+
- Android Studio + Android SDK
- JDK 17

## 步骤

```bash
# 1. 构建前端（API 指向你的后端地址）
cd frontend
# 编辑 .env.production
# VITE_API_BASE=http://你的服务器IP:8000/api/v1
npm install && npm run build

# 2. 初始化 Capacitor（首次）
cd ../packaging/android
npm init -y
npm install @capacitor/core @capacitor/cli @capacitor/android
npx cap init "模切流程系统" "com.diecutting.app" --web-dir ../../frontend/dist
npx cap add android

# 3. 同步并打开 Android Studio
npx cap sync android
npx cap open android

# 4. 在 Android Studio 中: Build → Build Bundle(s) / APK(s) → Build APK(s)
```

## 注意

- 手机与后端需同一网络，或后端有公网 HTTPS
- Android 9+ 默认禁止明文 HTTP，需在 `android/app/src/main/AndroidManifest.xml` 增加:
  `android:usesCleartextTraffic="true"`（仅内网调试）
- 生产环境请使用 HTTPS

## 无法在本 CI 环境直接产出 APK 的原因

打包需要完整 Android SDK / 模拟器签名环境，当前沙箱不具备，请在本机 Android Studio 完成最后一步。
