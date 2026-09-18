# 🤖 AI智能体管理中心

一个可配置本地模型、接入QQ的多智能体管理平台。

**在线预览：** https://excuse-2580.github.io/ai.com/

## ✨ 功能特性

- 🎭 **多智能体管理** — 自由创建/编辑/删除AI智能体
- ⚙️ **人设设定** — 自定义System Prompt，定义角色性格
- 🤖 **本地模型** — 支持 Ollama（llama3/qwen/deepseek等）
- 🌐 **API模型** — 支持 OpenAI / Claude / DeepSeek 等
- 💬 **QQ接入** — NoneBot2 框架，支持 go-cqhttp / Lagrange / Mirai
- 🔗 **群白名单** — 可限制智能体只在特定QQ群响应
- ⚡ **对话历史** — 自动维护多轮对话上下文
- 📱 **管理后台** — 简洁Web界面，配置一目了然

## 🏗️ 架构

```
ai-agent-project/
├── frontend/          # Web管理界面
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── backend/           # Python API服务
│   └── server.py      # 数据CRUD + 模型调用代理
├── nonebot/           # QQ机器人 (NoneBot2)
│   ├── bot.py         # 核心逻辑
│   └── nonebot.yml    # 配置
└── config/            # 运行时数据
    ├── agents.json    # 智能体数据
    └── model_config.json  # 模型配置
```

## 🚀 快速部署

### Web管理界面 → GitHub Pages

前端文件在 `frontend/` 目录，直接部署到 GitHub Pages 即可。

### 后端服务部署

```bash
cd backend
pip install -r requirements.txt
python server.py
```

### QQ机器人部署

```bash
cd nonebot
pip install nonebot2 nonebot-adapter-onebot httpx
nb run
```

## ⚙️ 模型配置

### Ollama（推荐本地）

```bash
# 安装Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 下载模型
ollama pull llama3
ollama pull qwen
ollama pull deepseek-r1

# 启动Ollama服务
ollama serve
```

### API模型

在管理后台配置：
- **OpenAI**: `https://api.openai.com/v1/chat/completions`
- **Claude**: `https://api.anthropic.com/v1/messages`
- **DeepSeek**: `https://api.deepseek.com/chat/completions`

## 🔗 QQ接入

推荐使用 [Lagrange.Core](https://github.com/LagrangeDev/Lagrange.Core) 或 [go-cqhttp](https://github.com/Mrs4s/go-cqhttp) 作为协议服务器：

1. 启动协议服务器（正向WS: `ws://localhost:8080`)
2. 修改 `nonebot/nonebot.yml` 中的 `SUPERUSERS` 为你的QQ号
3. 运行 `nb run`

## 📝 智能体配置说明

| 字段 | 说明 |
|------|------|
| 名称 | 智能体显示名 |
| 头像Emoji | 卡片显示的图标 |
| 人设设定 | System Prompt，决定AI的性格和行为 |
| 模型 | 留空使用全局配置，或指定 `ollama:llama3` / `api:openai` |
| 触发词 | 消息以该词开头时触发该智能体 |
| 群白名单 | 留空表示所有群可用，填群号则仅限指定群 |
| 对话上限 | 历史消息保留轮数 |

## 📄 许可证

MIT License
