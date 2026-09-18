/**
 * AI智能体管理中心 - 前端逻辑
 */

// 数据存储
const STORAGE_KEY = 'ai_agents_data';
const CONFIG_KEY = 'ai_model_config';

// 加载数据
function loadAgents() {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
}

// 保存数据
function saveAgents(agents) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(agents));
    renderAgents();
    updateStats();
}

// 加载模型配置
function loadModelConfig() {
    const data = localStorage.getItem(CONFIG_KEY);
    return data ? JSON.parse(data) : {
        ollama: { url: 'http://localhost:11434', models: [] },
        api: { type: 'openai', url: '', key: '', defaultModel: 'gpt-4o-mini' }
    };
}

// 保存模型配置
function saveModelConfigToStorage(config) {
    localStorage.setItem(CONFIG_KEY, JSON.stringify(config));
    updateStats();
}

// 更新统计
function updateStats() {
    const agents = loadAgents();
    const config = loadModelConfig();
    const active = agents.filter(a => a.active !== false).length;

    document.getElementById('agentCount').textContent = agents.length;
    document.getElementById('activeCount').textContent = active;

    const hasOllama = config.ollama?.url && config.ollama.models?.length > 0;
    const hasApi = config.api?.url && config.api.key;
    const modelStatus = document.getElementById('modelStatus');
    if (hasOllama) {
        modelStatus.textContent = 'Ollama ✓';
        modelStatus.style.color = 'var(--success)';
    } else if (hasApi) {
        modelStatus.textContent = 'API ✓';
        modelStatus.style.color = 'var(--success)';
    } else {
        modelStatus.textContent = '未配置';
        modelStatus.style.color = 'var(--text-muted)';
    }
}

// 渲染智能体列表
function renderAgents() {
    const agents = loadAgents();
    const grid = document.getElementById('agentsGrid');

    if (agents.length === 0) {
        grid.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🎭</div>
                <div class="empty-text">还没有智能体</div>
                <div class="empty-sub">点击上方「创建智能体」开始</div>
            </div>
        `;
        return;
    }

    grid.innerHTML = agents.map(agent => `
        <div class="agent-card" data-id="${agent.id}">
            <div class="agent-header">
                <div class="agent-avatar">${agent.avatar || '🤖'}</div>
                <div class="agent-info">
                    <div class="agent-name">${escapeHtml(agent.name)}</div>
                    <div class="agent-model">${escapeHtml(agent.model || '默认模型')}</div>
                </div>
                <div class="agent-actions">
                    <button class="agent-actions btn-toggle ${agent.active === false ? 'off' : ''}"
                            onclick="toggleAgent('${agent.id}')"
                            title="${agent.active === false ? '启用' : '停用'}">
                        ${agent.active === false ? '⏸' : '▶'}
                    </button>
                    <button class="btn-edit" onclick="editAgent('${agent.id}')" title="编辑">✏️</button>
                    <button class="btn-delete" onclick="showDeleteModal('${agent.id}')" title="删除">🗑️</button>
                </div>
            </div>
            <div class="agent-prompt">${escapeHtml(agent.prompt || '暂无设定')}</div>
            <div class="agent-meta">
                <span class="agent-tag ${agent.active !== false ? 'active' : ''}">
                    ${agent.active !== false ? '● 运行中' : '○ 已停用'}
                </span>
                ${agent.trigger ? `<span class="agent-tag">触发词: ${escapeHtml(agent.trigger)}</span>` : ''}
                ${agent.groups ? `<span class="agent-tag">群白名单</span>` : ''}
                <span class="agent-tag">对话上限: ${agent.maxTurns || 20}</span>
            </div>
        </div>
    `).join('');
}

// HTML转义
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 显示创建弹窗
function showCreateModal() {
    document.getElementById('modalTitle').textContent = '创建智能体';
    document.getElementById('agentId').value = '';
    document.getElementById('agentName').value = '';
    document.getElementById('agentAvatar').value = '🤖';
    document.getElementById('agentPrompt').value = '';
    document.getElementById('agentModel').value = '';
    document.getElementById('agentGroups').value = '';
    document.getElementById('agentTrigger').value = '';
    document.getElementById('agentMaxTurns').value = '20';
    document.getElementById('agentModal').classList.add('active');
}

// 编辑智能体
function editAgent(id) {
    const agents = loadAgents();
    const agent = agents.find(a => a.id === id);
    if (!agent) return;

    document.getElementById('modalTitle').textContent = '编辑智能体';
    document.getElementById('agentId').value = agent.id;
    document.getElementById('agentName').value = agent.name;
    document.getElementById('agentAvatar').value = agent.avatar || '🤖';
    document.getElementById('agentPrompt').value = agent.prompt || '';
    document.getElementById('agentModel').value = agent.model || '';
    document.getElementById('agentGroups').value = agent.groups || '';
    document.getElementById('agentTrigger').value = agent.trigger || '';
    document.getElementById('agentMaxTurns').value = agent.maxTurns || 20;
    document.getElementById('agentModal').classList.add('active');
}

// 保存智能体
function saveAgent() {
    const id = document.getElementById('agentId').value;
    const name = document.getElementById('agentName').value.trim();
    const avatar = document.getElementById('agentAvatar').value.trim() || '🤖';
    const prompt = document.getElementById('agentPrompt').value.trim();
    const model = document.getElementById('agentModel').value;
    const groups = document.getElementById('agentGroups').value.trim();
    const trigger = document.getElementById('agentTrigger').value.trim();
    const maxTurns = parseInt(document.getElementById('agentMaxTurns').value) || 20;

    if (!name) {
        alert('请输入智能体名称');
        return;
    }

    const agents = loadAgents();

    if (id) {
        // 编辑
        const idx = agents.findIndex(a => a.id === id);
        if (idx !== -1) {
            agents[idx] = { ...agents[idx], name, avatar, prompt, model, groups, trigger, maxTurns };
        }
    } else {
        // 新建
        agents.push({
            id: 'agent_' + Date.now(),
            name,
            avatar,
            prompt,
            model,
            groups,
            trigger,
            maxTurns,
            active: true,
            createdAt: new Date().toISOString(),
            conversations: []
        });
    }

    saveAgents(agents);
    closeModal();
}

// 关闭弹窗
function closeModal() {
    document.getElementById('agentModal').classList.remove('active');
}

// 切换启用状态
function toggleAgent(id) {
    const agents = loadAgents();
    const idx = agents.findIndex(a => a.id === id);
    if (idx !== -1) {
        agents[idx].active = agents[idx].active === false ? true : false;
        saveAgents(agents);
    }
}

// 删除相关
let deleteTargetId = null;

function showDeleteModal(id) {
    const agents = loadAgents();
    const agent = agents.find(a => a.id === id);
    if (!agent) return;
    deleteTargetId = id;
    document.getElementById('deleteName').textContent = agent.name;
    document.getElementById('deleteModal').classList.add('active');
}

function closeDeleteModal() {
    document.getElementById('deleteModal').classList.remove('active');
    deleteTargetId = null;
}

function confirmDelete() {
    if (!deleteTargetId) return;
    const agents = loadAgents().filter(a => a.id !== deleteTargetId);
    saveAgents(agents);
    closeDeleteModal();
}

// 模型配置弹窗
function showModelConfig() {
    const config = loadModelConfig();
    document.getElementById('ollamaUrl').value = config.ollama?.url || 'http://localhost:11434';
    document.getElementById('ollamaModels').value = (config.ollama?.models || []).join('\n');
    document.getElementById('apiType').value = config.api?.type || 'openai';
    document.getElementById('apiUrl').value = config.api?.url || '';
    document.getElementById('apiKey').value = config.api?.key || '';
    document.getElementById('apiDefaultModel').value = config.api?.defaultModel || 'gpt-4o-mini';
    document.getElementById('ollamaStatus').textContent = '';
    document.getElementById('apiStatus').textContent = '';
    document.getElementById('modelModal').classList.add('active');
}

function closeModelModal() {
    document.getElementById('modelModal').classList.remove('active');
}

function saveModelConfig() {
    const config = {
        ollama: {
            url: document.getElementById('ollamaUrl').value.trim(),
            models: document.getElementById('ollamaModels').value.split('\n').map(m => m.trim()).filter(m => m)
        },
        api: {
            type: document.getElementById('apiType').value,
            url: document.getElementById('apiUrl').value.trim(),
            key: document.getElementById('apiKey').value.trim(),
            defaultModel: document.getElementById('apiDefaultModel').value.trim()
        }
    };
    saveModelConfigToStorage(config);
    closeModelModal();
}

// 测试Ollama连接
async function testOllama() {
    const url = document.getElementById('ollamaUrl').value.trim();
    const statusEl = document.getElementById('ollamaStatus');
    statusEl.textContent = '测试中...';
    statusEl.className = 'status-msg';

    try {
        const resp = await fetch(`${url}/api/tags`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000)
        });
        if (resp.ok) {
            const data = await resp.json();
            const count = data.models?.length || 0;
            statusEl.textContent = `✓ 连接成功 (${count} 个模型)`;
            statusEl.className = 'status-msg ok';
        } else {
            statusEl.textContent = `✗ 响应异常: ${resp.status}`;
            statusEl.className = 'status-msg err';
        }
    } catch (e) {
        statusEl.textContent = `✗ 连接失败: ${e.message}`;
        statusEl.className = 'status-msg err';
    }
}

// 测试API连接
async function testApi() {
    const url = document.getElementById('apiUrl').value.trim();
    const key = document.getElementById('apiKey').value.trim();
    const statusEl = document.getElementById('apiStatus');
    statusEl.textContent = '测试中...';
    statusEl.className = 'status-msg';

    if (!url || !key) {
        statusEl.textContent = '请填写API地址和密钥';
        statusEl.className = 'status-msg err';
        return;
    }

    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${key}`
            },
            body: JSON.stringify({
                model: document.getElementById('apiDefaultModel').value || 'gpt-4o-mini',
                messages: [{ role: 'user', content: 'hi' }],
                max_tokens: 5
            }),
            signal: AbortSignal.timeout(8000)
        });

        if (resp.ok) {
            statusEl.textContent = '✓ 连接成功';
            statusEl.className = 'status-msg ok';
        } else {
            const err = await resp.json().catch(() => ({}));
            statusEl.textContent = `✗ 错误: ${err.error?.message || resp.status}`;
            statusEl.className = 'status-msg err';
        }
    } catch (e) {
        statusEl.textContent = `✗ 连接失败: ${e.message}`;
        statusEl.className = 'status-msg err';
    }
}

// 点击弹窗背景关闭
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('active');
    }
});

// 键盘ESC关闭弹窗
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        document.querySelectorAll('.modal.active').forEach(m => m.classList.remove('active'));
    }
});

// 导出数据（供后端读取）
function exportAgentsJson() {
    return JSON.stringify(loadAgents(), null, 2);
}

function exportConfigJson() {
    return JSON.stringify(loadModelConfig(), null, 2);
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    renderAgents();
    updateStats();
});
