"""
后端 API 服务
- 提供智能体数据 CRUD 接口
- 供 NoneBot 机器人读取配置
- 提供模型调用代理（可选）
"""

import json
import os
import asyncio
import httpx
from aiohttp import web
from pathlib import Path

# ==================== 路径配置 ====================

BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_DIR.mkdir(exist_ok=True)

AGENTS_FILE = CONFIG_DIR / "agents.json"
MODEL_FILE = CONFIG_DIR / "model_config.json"
PORT = int(os.getenv("API_PORT", "8090"))

# ==================== 辅助函数 ====================

def read_json(path, default=None):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default or {}

def write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return True

# ==================== 路由 ====================

routes = web.RouteTableDef()

# 健康检查
@routes.get("/health")
async def health(request):
    return web.json_response({"status": "ok", "version": "1.0.0"})

# ---- 智能体 CRUD ----

@routes.get("/api/agents")
async def get_agents(request):
    """获取所有智能体"""
    data = read_json(AGENTS_FILE, [])
    return web.json_response(data)

@routes.post("/api/agents")
async def create_agent(request):
    """创建智能体"""
    body = await request.json()
    agents = read_json(AGENTS_FILE, [])
    agent = {
        "id": body.get("id") or f"agent_{len(agents) + 1}",
        "name": body.get("name", "未命名"),
        "avatar": body.get("avatar", "🤖"),
        "prompt": body.get("prompt", ""),
        "model": body.get("model", ""),
        "groups": body.get("groups", ""),
        "trigger": body.get("trigger", ""),
        "maxTurns": body.get("maxTurns", 20),
        "active": body.get("active", True),
        "createdAt": body.get("createdAt", ""),
        "conversations": []
    }
    agents.append(agent)
    write_json(AGENTS_FILE, agents)
    return web.json_response(agent, status=201)

@routes.put("/api/agents/{agent_id}")
async def update_agent(request):
    """更新智能体"""
    agent_id = request.match_info["agent_id"]
    body = await request.json()
    agents = read_json(AGENTS_FILE, [])
    for i, a in enumerate(agents):
        if a["id"] == agent_id:
            agents[i] = {**a, **body, "id": agent_id}
            write_json(AGENTS_FILE, agents)
            return web.json_response(agents[i])
    return web.json_response({"error": "Not found"}, status=404)

@routes.delete("/api/agents/{agent_id}")
async def delete_agent(request):
    """删除智能体"""
    agent_id = request.match_info["agent_id"]
    agents = read_json(AGENTS_FILE, [])
    new_agents = [a for a in agents if a["id"] != agent_id]
    if len(new_agents) == len(agents):
        return web.json_response({"error": "Not found"}, status=404)
    write_json(AGENTS_FILE, new_agents)
    return web.json_response({"ok": True})

# ---- 模型配置 ----

@routes.get("/api/config/model")
async def get_model_config(request):
    return web.json_response(read_json(MODEL_FILE, {
        "ollama": {"url": "http://localhost:11434", "models": []},
        "api": {"type": "openai", "url": "", "key": "", "defaultModel": "gpt-4o-mini"}
    }))

@routes.post("/api/config/model")
async def save_model_config(request):
    body = await request.json()
    write_json(MODEL_FILE, body)
    return web.json_response({"ok": True})

@routes.post("/api/config/test/ollama")
async def test_ollama(request):
    """测试 Ollama 连接"""
    body = await request.json()
    url = body.get("url", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{url}/api/tags")
            if resp.ok:
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                return web.json_response({"ok": True, "models": models})
            return web.json_response({"ok": False, "error": f"HTTP {resp.status_code}"}, status=502)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=502)

@routes.post("/api/config/test/api")
async def test_api(request):
    """测试 API 连接"""
    body = await request.json()
    url = body.get("url", "")
    key = body.get("key", "")
    model = body.get("defaultModel", "gpt-4o-mini")
    api_type = body.get("type", "openai")
    try:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 5
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.ok:
                return web.json_response({"ok": True})
            err = await resp.json().catch(lambda: {})
            return web.json_response({"ok": False, "error": err.get("error", {}).get("message", str(resp.status_code))}, status=502)
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=502)

# ---- 模型调用代理 ----

@routes.post("/api/chat")
async def chat_proxy(request):
    """统一的聊天接口"""
    body = await request.json()
    agent_id = body.get("agent_id")
    message = body.get("message", "")
    history = body.get("history", [])
    model_ref = body.get("model", "")

    config = read_json(MODEL_FILE, {})
    agents = read_json(AGENTS_FILE, [])
    agent = next((a for a in agents if a["id"] == agent_id), agents[0]) if agents else None
    system_prompt = agent.get("prompt", "你是一个有帮助的AI助手") if agent else "你是一个有帮助的AI助手"

    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]

    model_ref = model_ref or agent.get("model", "") if agent else ""

    try:
        if model_ref.startswith("ollama:"):
            model_name = model_ref[7:]
            ollama_cfg = config.get("ollama", {})
            url = f"{ollama_cfg.get('url', 'http://localhost:11434').rstrip('/')}/api/chat"
            payload = {
                "model": model_name,
                "messages": messages[-20:],
                "stream": False
            }
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return web.json_response({"reply": data["message"]["content"]})

        else:
            api_cfg = config.get("api", {})
            api_url = api_cfg.get("url", "")
            api_key = api_cfg.get("key", "")
            api_type = api_cfg.get("type", "openai")
            default_model = api_cfg.get("defaultModel", "gpt-4o-mini")
            if not api_url:
                return web.json_response({"error": "API未配置"}, status=400)
            headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
            if api_type == "claude":
                headers["x-api-key"] = api_key
                headers["anthropic-version"] = "2023-06-01"
                filtered = [m for m in messages if m["role"] != "system"]
                system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
                payload = {"model": default_model, "messages": filtered[-20:], "max_tokens": 2048}
                if system_msg:
                    payload["system"] = system_msg
            else:
                payload = {"model": default_model, "messages": messages[-20:], "max_tokens": 2048}
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(api_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if api_type == "claude":
                    reply = data["content"][0]["text"]
                else:
                    reply = data["choices"][0]["message"]["content"]
                return web.json_response({"reply": reply})

    except httpx.TimeoutException:
        return web.json_response({"error": "请求超时"}, status=504)
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# ==================== 启动 ====================

app = web.Application()
app.add_routes(routes)

if __name__ == "__main__":
    print(f"🚀 API服务启动: http://0.0.0.0:{PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)
