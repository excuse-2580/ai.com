"""
AI智能体 QQ机器人 - NoneBot2
支持多智能体切换、本地Ollama模型、API模型
"""

import os
import re
import json
import asyncio
import httpx
from nonebot import on_message, on_command, on_startup, require
from nonebot.adapters.onebot.v11 import GROUP, PRIVATE, Message, MessageSegment
from nonebot.config import Config
from nonebot.params import CommandArg, EventMessage, Event
from nonebot.permission import SUPERUSER

# ==================== 配置加载 ====================

CONFIG_PATH = os.getenv("MODEL_CONFIG_PATH", "./config/model_config.json")
AGENTS_PATH = os.getenv("AGENTS_DATA_PATH", "./config/agents.json")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# 全局对话上下文: {user_id: {agent_id: [{"role": "user/assistant", "content": "..."}]}}
conversation_cache: dict[str, dict[str, list]] = {}
# 最大历史消息数
MAX_HISTORY = 40


def load_config() -> dict:
    """加载模型配置"""
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {
            "ollama": {"url": "http://localhost:11434", "models": ["llama3"]},
            "api": {"type": "openai", "url": "", "key": "", "defaultModel": "gpt-4o-mini"}
        }


def load_agents() -> list:
    """加载智能体列表"""
    try:
        with open(AGENTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_agents(agents: list):
    """保存智能体列表"""
    os.makedirs(os.path.dirname(AGENTS_PATH), exist_ok=True)
    with open(AGENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(agents, f, ensure_ascii=False, indent=2)


def get_agent_by_trigger(agents: list, text: str, group_id: str | None = None) -> dict | None:
    """根据触发词或关键词匹配智能体"""
    text_lower = text.lower().strip()
    for agent in agents:
        if not agent.get("active", True):
            continue
        # 检查群白名单
        groups = agent.get("groups", "")
        if groups:
            allowed = [g.strip() for g in groups.split(",") if g.strip()]
            if allowed and group_id and str(group_id) not in allowed:
                continue
        # 精确触发词匹配
        trigger = agent.get("trigger", "").strip()
        if trigger and text_lower.startswith(trigger.lower()):
            return agent
        # 关键词匹配（@机器人 关键词）
        if trigger and trigger in text_lower:
            return agent
    return agents[0] if agents else None


# ==================== LLM 调用 ====================

async def call_ollama(model: str, messages: list[dict], url: str = None) -> str:
    """调用 Ollama 本地模型"""
    config = load_config()
    base_url = url or config.get("ollama", {}).get("url", OLLAMA_URL)
    url = f"{base_url.rstrip('/')}/api/chat"

    # 转换为 Ollama 格式
    ollama_messages = []
    for m in messages[-MAX_HISTORY:]:
        ollama_messages.append({
            "role": m["role"],
            "content": m["content"]
        })

    payload = {
        "model": model,
        "messages": ollama_messages,
        "stream": False,
        "options": {
            "num_predict": 2048,
            "temperature": 0.8
        }
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]


async def call_api_model(messages: list[dict], model: str = None, api_type: str = None) -> str:
    """调用 API 模型（OpenAI兼容 / Claude / DeepSeek）"""
    config = load_config()
    api_cfg = config.get("api", {})
    api_type = api_type or api_cfg.get("type", "openai")
    api_url = api_cfg.get("url", "")
    api_key = api_cfg.get("key", "")
    default_model = model or api_cfg.get("defaultModel", "gpt-4o-mini")

    if not api_url or not api_key:
        return "⚠️ API未配置，请先在管理后台配置模型"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # OpenAI 兼容格式
    if api_type in ("openai", "deepseek", "custom"):
        url = api_url
        payload = {
            "model": default_model,
            "messages": messages[-MAX_HISTORY:],
            "max_tokens": 2048,
            "temperature": 0.8
        }
        if api_type == "deepseek":
            payload["model"] = default_model or "deepseek-chat"

    # Claude 格式
    elif api_type == "claude":
        url = api_url or "https://api.anthropic.com/v1/messages"
        if "anthropic" not in api_url:
            url = "https://api.anthropic.com/v1/messages"
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
        system_msg = ""
        filtered = []
        for m in messages[-MAX_HISTORY:]:
            if m["role"] == "system":
                system_msg = m["content"]
            else:
                filtered.append(m)
        payload = {
            "model": default_model or "claude-3-haiku-20240307",
            "max_tokens": 2048,
            "messages": filtered
        }
        if system_msg:
            payload["system"] = system_msg

    else:
        return f"⚠️ 不支持的API类型: {api_type}"

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        if api_type == "claude":
            return data["content"][0]["text"]
        return data["choices"][0]["message"]["content"]


async def chat_with_agent(agent: dict, messages: list[dict]) -> str:
    """根据智能体配置调用对应模型"""
    model_ref = agent.get("model", "")

    if model_ref.startswith("ollama:"):
        model = model_ref[7:]
        return await call_ollama(model, messages)
    elif model_ref.startswith("api:"):
        api_type = model_ref[4:]  # api:openai -> openai
        return await call_api_model(messages, api_type=api_type)
    else:
        # 使用全局配置
        config = load_config()
        if config.get("ollama", {}).get("models"):
            return await call_ollama(
                config["ollama"]["models"][0],
                messages,
                url=config["ollama"].get("url")
            )
        elif config.get("api", {}).get("url"):
            return await call_api_model(messages)
        else:
            return "⚠️ 未配置任何模型，请先在管理后台配置"


# ==================== 指令处理 ====================

# 管理员命令
admin_list = on_command("ai列表", permission=SUPERUSER, priority=1)
admin_add = on_command("ai添加", permission=SUPERUSER, priority=1)
admin_del = on_command("ai删除", permission=SUPERUSER, priority=1)
admin_reload = on_command("ai重载", permission=SUPERUSER, priority=1)
admin_status = on_command("ai状态", permission=SUPERUSER, priority=1)


@admin_list.handle()
async def list_agents():
    agents = load_agents()
    if not agents:
        await admin_list.finish("📋 暂无已配置的智能体")
    msg = "📋 智能体列表：\n"
    for i, a in enumerate(agents, 1):
        status = "✅" if a.get("active", True) else "❌"
        msg += f"{i}. {status} {a['name']} ({a.get('avatar','🤖')}) - {a.get('model','默认')}\n"
        msg += f"   设定: {a.get('prompt','无')[:50]}...\n"
    await admin_list.finish(msg)


@admin_reload.handle()
async def reload_agents():
    global conversation_cache
    conversation_cache = {}
    await admin_reload.finish("✅ 已重置所有对话上下文")


@admin_status.handle()
async def check_status():
    config = load_config()
    agents = load_agents()
    ollama_ok = False
    api_ok = False

    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            r = await client.get(f"{config['ollama']['url']}/api/tags")
            ollama_ok = r.ok
        except Exception:
            pass

    msg = "🔧 系统状态\n"
    msg += f"🤖 智能体数量: {len(agents)}\n"
    msg += f"✅ Ollama: {'在线' if ollama_ok else '离线'} ({config['ollama']['url']})\n"
    msg += f"🌐 API: {'已配置' if config['api']['url'] else '未配置'}\n"
    msg += f"💬 对话缓存: {len(conversation_cache)} 个用户"
    await admin_status.finish(msg)


# ==================== 群聊/私聊消息处理 ====================

# 匹配所有消息，进行智能体路由
chat_handler = on_message(priority=5)


@chat_handler.handle()
async def handle_chat(event: Event, message: Message = EventMessage()):
    """核心聊天逻辑"""
    # 排除超级用户自身消息（避免循环）
    # 如果 sender_id 是超级用户，跳过（防止机器人回复自己）

    raw_text = str(message).strip()
    if not raw_text:
        return

    # 获取群组/用户ID
    group_id = None
    user_id = str(event.get_user_id())

    try:
        segment_list = message if hasattr(message, '__iter__') else [message]
        for seg in segment_list:
            if hasattr(seg, 'type') and seg.type == 'at' and hasattr(seg, 'data'):
                # 被@的消息
                pass
    except Exception:
        pass

    # 加载智能体和配置
    agents = load_agents()
    if not agents:
        await chat_handler.finish("⚠️ 暂无可用的智能体，请联系管理员配置")

    # 匹配智能体
    agent = get_agent_by_trigger(agents, raw_text, group_id)
    if not agent:
        return  # 未匹配到任何智能体

    # 初始化对话历史
    cache_key = f"{user_id}_{agent['id']}"
    if cache_key not in conversation_cache:
        conversation_cache[cache_key] = []

    history = conversation_cache[cache_key]

    # 构建消息列表
    system_prompt = agent.get("prompt", "你是一个有帮助的AI助手")
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": raw_text}]

    # 调用模型
    try:
        reply = await chat_with_agent(agent, messages)
    except httpx.TimeoutException:
        await chat_handler.finish("⏰ 请求超时，请稍后重试")
    except httpx.HTTPStatusError as e:
        await chat_handler.finish(f"❌ 模型请求失败: {e.response.status_code}")
    except Exception as e:
        await chat_handler.finish(f"❌ 出错: {str(e)}")

    # 保存对话历史
    history.append({"role": "user", "content": raw_text})
    history.append({"role": "assistant", "content": reply})
    max_turns = agent.get("maxTurns", 20)
    if len(history) > max_turns * 2:
        conversation_cache[cache_key] = history[-max_turns * 2:]

    await chat_handler.finish(reply)


# ==================== 启动提示 ====================

@on_startup
async def startup():
    print("=" * 50)
    print("🤖 AI智能体 QQ 机器人已启动")
    print("=" * 50)
    agents = load_agents()
    print(f"📋 已加载 {len(agents)} 个智能体")
    config = load_config()
    print(f"🤖 Ollama: {config.get('ollama', {}).get('url', '未配置')}")
    print(f"🌐 API: {config.get('api', {}).get('url', '未配置')}")
    print("=" * 50)
