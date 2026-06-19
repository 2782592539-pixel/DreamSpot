// MZC 移动中控 API 文档 - 前端逻辑

const state = {
  schema: null,
  healthTimer: null,
};

const $ = (id) => document.getElementById(id);

// 把 JSON 漂亮地格式化(2 空格缩进)
function formatJSON(obj) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch {
    return String(obj);
  }
}

// 把 OpenAPI path 模板 (/api/tasks/{task_id}) 转成可点击的 sample
function pathWithSample(tpl) {
  return tpl.replace(/\{(\w+)\}/g, (_, name) => '<' + name + '>');
}

// 从 path 模板中提取 path 参数名
function extractPathParams(tpl) {
  const out = [];
  tpl.replace(/\{(\w+)\}/g, (_, name) => { out.push(name); return ''; });
  return out;
}

// 主入口
async function init() {
  try {
    const res = await fetch('/openapi.json');
    if (!res.ok) throw new Error('openapi.json ' + res.status);
    state.schema = await res.json();
    renderSidebar();
    renderEndpoints();
    bindGlobalClicks();
  } catch (e) {
    $('endpoints').innerHTML = '<p style="color:var(--error)">加载 openapi.json 失败: ' + e.message + '</p>';
  }
  startHealthPolling();
}

function renderSidebar() {
  const navList = $('nav-list');
  navList.innerHTML = '';
  // 按 tag 分组
  const groups = {};
  for (const [path, methods] of Object.entries(state.schema.paths)) {
    for (const [method, op] of Object.entries(methods)) {
      if (method.startsWith('x-')) continue;
      const tag = (op.tags && op.tags[0]) || '未分类';
      if (!groups[tag]) groups[tag] = [];
      groups[tag].push({ method, path, op });
    }
  }
  for (const [tagName, items] of Object.entries(groups)) {
    const group = document.createElement('div');
    group.className = 'nav-group';
    const nameEl = document.createElement('div');
    nameEl.className = 'nav-group-name';
    nameEl.textContent = tagName;
    group.appendChild(nameEl);
    for (const item of items) {
      const link = document.createElement('a');
      link.href = '#op-' + item.method.toUpperCase() + '-' + item.path;
      link.className = 'nav-link';
      link.textContent = item.method.toUpperCase() + ' ' + item.path;
      link.dataset.target = 'op-' + item.method.toUpperCase() + '-' + item.path;
      group.appendChild(link);
    }
    navList.appendChild(group);
  }
}

function renderEndpoints() {
  const container = $('endpoints');
  container.innerHTML = '';
  for (const [path, methods] of Object.entries(state.schema.paths)) {
    for (const [method, op] of Object.entries(methods)) {
      if (method.startsWith('x-')) continue;
      container.appendChild(renderCard(method, path, op));
    }
  }
}

function renderCard(method, path, op) {
  const card = document.createElement('article');
  card.className = 'endpoint';
  card.id = 'op-' + method.toUpperCase() + '-' + path;

  const head = document.createElement('div');
  head.className = 'endpoint-head';
  head.innerHTML =
    '<span class="method-badge ' + method + '">' + method.toUpperCase() + '</span>' +
    '<span class="endpoint-path">' + pathWithSample(path) + '</span>' +
    '<span class="endpoint-summary">' + (op.summary || '') + '</span>';
  head.addEventListener('click', () => card.classList.toggle('open'));
  card.appendChild(head);

  const body = document.createElement('div');
  body.className = 'endpoint-body';
  if (op.description) {
    const desc = document.createElement('p');
    desc.className = 'endpoint-description';
    desc.textContent = op.description;
    body.appendChild(desc);
  }
  // Path 参数输入
  const pathParams = extractPathParams(path);
  const trySec = document.createElement('div');
  trySec.className = 'try-section';
  pathParams.forEach((p) => {
    const row = document.createElement('div');
    row.className = 'try-row';
    row.innerHTML =
      '<span class="try-label">' + p + ':</span>' +
      '<input class="try-input" data-path-param="' + p + '" placeholder="请输入 ' + p + '">';
    trySec.appendChild(row);
  });
  // 执行按钮 + 响应
  const actions = document.createElement('div');
  actions.className = 'try-row';
  actions.innerHTML =
    '<span class="try-label"></span>' +
    '<button class="btn btn-primary" data-action="try">执行</button>' +
    '<button class="btn" data-action="copy" disabled>复制响应</button>';
  trySec.appendChild(actions);
  const responseBox = document.createElement('div');
  responseBox.style.display = 'none';
  body.appendChild(trySec);
  body.appendChild(responseBox);

  // 绑定按钮
  actions.querySelector('[data-action="try"]').addEventListener('click', async (ev) => {
    ev.stopPropagation();
    const btn = ev.currentTarget;
    btn.disabled = true;
    btn.textContent = '执行中...';
    responseBox.style.display = 'block';
    responseBox.innerHTML = '<span class="response-status">...</span><pre class="response-box">请求中</pre>';
    try {
      const params = {};
      trySec.querySelectorAll('[data-path-param]').forEach((inp) => {
        params[inp.dataset.pathParam] = inp.value;
      });
      const result = await tryEndpoint(method, path, params);
      const cls = result.status >= 200 && result.status < 300 ? 'ok' : 'error';
      responseBox.innerHTML =
        '<span class="response-status ' + cls + '">HTTP ' + result.status + '</span>' +
        '<pre class="response-box">' + formatJSON(result.body) + '</pre>';
      const copyBtn = actions.querySelector('[data-action="copy"]');
      copyBtn.disabled = false;
      copyBtn.onclick = () => {
        navigator.clipboard.writeText(formatJSON(result.body));
      };
    } catch (e) {
      responseBox.innerHTML =
        '<span class="response-status error">ERROR</span>' +
        '<pre class="response-box">' + e.message + '</pre>';
    } finally {
      btn.disabled = false;
      btn.textContent = '执行';
    }
  });

  card.appendChild(body);
  return card;
}

async function tryEndpoint(method, path, pathParams) {
  // 替换路径参数
  let url = path;
  for (const [k, v] of Object.entries(pathParams)) {
    url = url.replace('{' + k + '}', encodeURIComponent(v || ''));
  }
  const res = await fetch(url, { method: method.toUpperCase() });
  const text = await res.text();
  let body;
  try { body = JSON.parse(text); }
  catch { body = text; }
  return { status: res.status, body };
}

function bindGlobalClicks() {
  document.querySelectorAll('.nav-link').forEach((link) => {
    link.addEventListener('click', (ev) => {
      ev.preventDefault();
      const id = link.dataset.target;
      const target = document.getElementById(id);
      if (!target) return;
      // 自动展开
      target.classList.add('open');
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      // 高亮 1.5s
      link.classList.add('highlight');
      setTimeout(() => link.classList.remove('highlight'), 1500);
    });
  });
}

function startHealthPolling() {
  const dot = $('health-dot');
  const text = $('health-text');
  const time = $('health-time');
  async function check() {
    try {
      const res = await fetch('/api/system/status');
      const data = await res.json();
      if (data.status === 'ok') {
        dot.dataset.state = 'ok';
        text.textContent = '在线';
        const t = new Date(data.timestamp);
        time.textContent = '上次同步: ' + t.toLocaleTimeString('zh-CN');
      } else {
        dot.dataset.state = 'error';
        text.textContent = '异常';
      }
    } catch (e) {
      dot.dataset.state = 'error';
      text.textContent = '无法连接';
    }
  }
  check();
  state.healthTimer = setInterval(check, 5000);
}

document.addEventListener('DOMContentLoaded', init);
