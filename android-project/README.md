# AI智能体 App - Android

## 概述

这是一个打包好的 Android 应用（APK），包含：
- Web管理界面（内置，无需联网）
- QQ机器人配置工具
- Ollama 本地模型连接器
- API模型配置

## 快速安装

1. 用手机访问 GitHub Releases 页面
2. 下载 `ai-agent-app.apk`
3. 安装（可能需要允许「安装未知来源应用」）
4. 打开 app 即可使用

## 首次配置

### 配置本地模型（Ollama）
1. 在电脑安装 Ollama：`curl -fsSL https://ollama.com/install.sh | sh`
2. 下载模型：`ollama pull llama3`
3. 启动服务：`ollama serve`
4. 确认电脑和手机在同一局域网
5. 在 App 中填入电脑 IP（如 `http://192.168.1.100:11434`）

### QQ接入
1. 手机上需要安装 QQ
2. 在 App 中配置 QQ 机器人参数
3. 对接 go-cqhttp / Lagrange（需自行部署）

## 界面预览

- 主页：智能体列表
- 创建智能体：设置名称/头像/人设
- 模型配置：Ollama / API 切换
- QQ设置：接入参数

## 技术说明

- 使用 Android WebView 加载本地 HTML
- 所有数据存储在手机本地（localStorage）
- 支持离线使用核心管理功能
- 在线功能需要连接 Ollama 服务器

## 构建自己的 APK

如果需要修改后重新打包：

### 环境要求
- Android Studio（推荐）
- 或使用 online compiler

### 步骤
1. 打开 Android Studio
2. 选择「Open Existing Project」
3. 导入本目录
4. 修改 `assets/` 中的 HTML/JS/CSS
5. Build → Build Bundle(s) / APK(s) → Build APK
6. 在 `app/build/outputs/apk/debug/` 找到 APK

### 或用命令行
```bash
cd android-project
./gradlew assembleDebug
# APK 在 app/build/outputs/apk/debug/app-debug.apk
```
