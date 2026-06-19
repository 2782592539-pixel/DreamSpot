# MZC 自定义 API 文档页 - 设计文档

> 日期:2026-06-19
> 作者:H-yue (与 Claude Code 协作)
> 状态:已实现 (commits: e309c26, fd07348, 801cbbc, 8f15cfe, bb4766a, 0827340, 86514ec; merge 07a3a5c)
> 范围:仅替换 FastAPI 自带的 `/docs` (Swagger UI) 与 `/redoc`,为 Phase 1 已有 3 个 endpoint 提供中文 + 暗色技术风文档页

---

## 一、目标

把 MZC 当前默认的 Swagger UI 文档页(`http://127.0.0.1:8765/docs`)替换为:
1. **全中文界面** — 标签、按钮、字段描述、错误信息全部汉化
2. **暗色技术风视觉** — 暗背景、开发者友好的字号与配色
3. **保留"在线试调"能力** — 像 Swagger 一样能直接点按钮调用接口并看响应

### 非目标 (YAGNI)

- 完整管理后台 UI(任务增删改、运行历史图表) — 留给 Phase 8
- 用户登录界面 — 留给 Phase 5 (Cloudflare Access)
- 移动端原生 App — 用响应式 Web 即可
- 暗/亮主题切换 — 这次只做暗色,亮色后续再说

---

## 二、范围

### 包含

| # | 项 | 说明 |
|---|----|------|
| 1 | 一个新的静态首页 | `GET /` 返回中文 + 暗色 SPA |
| 2 | FastAPI OpenAPI 元数据中文化 | `tags`、`summary`、`Field(description=)` 改成中文 |
| 3 | 关闭默认 `/docs` 与 `/redoc` | `docs_url=None, redoc_url=None` |
| 4 | 前端 fetch `/openapi.json` 渲染 | 不写后端模板,纯前端拼装 |
| 5 | 在线试调 endpoint | GET 用 query,POST/PUT 用 JSON body |
| 6 | 健康指示器 | 5 秒轮询 `/api/system/status` |
| 7 | 响应式布局 | 桌面端双栏,手机端单栏 |

### 不包含

- 接口鉴权 / 登录 — Phase 5 引入 Cloudflare Access 后再补
- 主题切换(暗/亮) — YAGNI
- 任务增删改按钮 — Phase 8 范围
- i18n 框架(完整双语切换) — 只做中文一套

---

## 三、架构与数据流

### 3.1 请求流

```
浏览器 GET /
   ↓
FastAPI 路由 → backend/static/index.html (200, text/html)
   ↓
浏览器解析 HTML → 加载 /assets/app.css + /assets/app.js
   ↓
JS 启动 → fetch /openapi.json
   ↓
解析 OpenAPI schema,渲染侧边栏目录 + 主区 endpoint 卡片
   ↓
用户点"试一下"按钮 → fetch 调用对应 /api/... endpoint
   ↓
把响应 JSON 格式化展示在卡片底部
```

### 3.2 文件树

```
backend/
├── main.py                # 改:docs_url=None, redoc_url=None,新增 GET /,挂载 /assets
├── api/
│   ├── system.py          # 改:tags=["服务状态"],加 summary/description 中文
│   └── tasks.py           # 改:tags=["定时任务"],加 summary/description 中文
├── models/
│   └── task.py            # 改:Field(description=...) 全部中文
└── static/                # 新增
    ├── index.html
    ├── app.css
    └── app.js

tests/
├── test_home_page.py      # 新增:GET / 返回 200 + 引用 CSS/JS 存在
├── test_chinese_i18n.py   # 新增:openapi.json 含中文 tags/summary
└── (现有 21 个测试一个不破)
```

### 3.3 依赖

- **不引入新 PyPI 包** — 用 FastAPI 自带的 `StaticFiles` + `HTMLResponse`
- **不引入前端构建工具** — 原生 HTML/CSS/JS,无 npm/webpack/vite
- **不引入字体二进制** — 优先用系统字体,只在 CSS 里声明"如可用则用 JetBrains Mono / 苹方",不存在则退化

---

## 四、视觉设计

### 4.1 配色 (CSS 变量)

```css
--bg-primary:   #0d1117;   /* 主背景 */
--bg-card:      #161b22;   /* 卡片背景 */
--bg-elevated:  #1f242c;   /* 输入框/按钮 */
--border:       #30363d;   /* 描边 */
--text-primary: #c9d1d9;   /* 主文字 */
--text-muted:   #8b949e;   /* 次要文字 */
--accent:       #58a6ff;   /* 链接/主色 */
--get:          #58a6ff;   /* GET 方法 */
--post:         #3fb950;   /* POST 方法 */
--delete:       #f85149;   /* DELETE 方法 */
--put:          #d29922;   /* PUT 方法 */
--success:      #3fb950;   /* 成功指示 */
--error:        #f85149;   /* 错误指示 */
```

### 4.2 字体

```css
--font-mono: 'JetBrains Mono', 'Cascadia Code', 'Consolas', monospace;
--font-sans: 'Inter', 'PingFang SC', 'Microsoft YaHei', system-ui, sans-serif;
```

- 标题、按钮用 sans
- 路径、JSON、代码块用 mono

### 4.3 布局

**桌面端 (≥768px):**
```
┌──────────────────────────────────────────────────────────┐
│  ● MZC · 移动中控                          v0.1.0        │
│  ──────────────────────────────────────────────────────  │
│  服务状态: ● 在线    上次同步: 12:34:56                   │
│                                                          │
├──────────┬───────────────────────────────────────────────┤
│  目录     │  ▼ 服务状态                                    │
│  ─────── │    GET  /api/system/status                    │
│  服务状态 │    检查服务是否在线                            │
│  定时任务 │    [试一下]                                   │
│          │                                               │
│  ─────── │  ▼ 定时任务                                    │
│  关于     │    GET  /api/tasks                             │
│          │    列出所有定时任务                           │
│          │    [试一下]                                   │
│          │                                               │
│          │    GET  /api/tasks/{id}                       │
│          │    查看单个任务详情                           │
│          │    [试一下]  task_id: [______]                 │
│          │                                               │
└──────────┴───────────────────────────────────────────────┘
```

**手机端 (<768px):**
- 侧边栏折叠为顶部下拉选择器
- 主区单列,卡片占满
- 字号略放大(16px → 17px)

### 4.4 关键交互

| 元素 | 行为 |
|------|------|
| 侧边栏链接 | 点击平滑滚动到对应 endpoint 卡片,并高亮 1.5s |
| endpoint 卡片 | 默认折叠,点标题展开;URL 含 `#task-{id}` 时自动展开 |
| "试一下" 按钮 | 展开参数输入区,GET 显示 query 输入框,POST/PUT 显示 JSON textarea |
| "执行" 按钮 | fetch 调用,把响应格式化(2 空格缩进)显示在"响应"区域 |
| 响应状态码 | 200 绿底,4xx/5xx 红底 |
| 健康指示器 | 启动时调一次,5s 轮询;失败变灰并显示错误 |
| 复制按钮 | 复制 JSON 响应到剪贴板 |

---

## 五、组件设计

### 5.1 后端路由 (`backend/main.py`)

```python
app = FastAPI(
    title="MZC 移动中控",
    version="0.1.0",
    description="家用 Claude Code 移动控制中心",
    docs_url=None,      # 关闭 Swagger UI
    redoc_url=None,     # 关闭 ReDoc
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# 挂载静态资源
app.mount("/assets", StaticFiles(directory="backend/static"), name="assets")

@app.get("/", include_in_schema=False)
def home() -> HTMLResponse:
    index = Path("backend/static/index.html")
    return HTMLResponse(index.read_text(encoding="utf-8"))
```

### 5.2 Router 中文化

**`backend/api/system.py`:**
```python
router = APIRouter(
    prefix="/api/system",
    tags=["服务状态"],
)

@router.get("/status", summary="获取服务状态", description="检查 MZC 服务是否在线,返回版本号与时间戳。")
def get_status() -> dict: ...
```

**`backend/api/tasks.py`:**
```python
router = APIRouter(
    prefix="/api/tasks",
    tags=["定时任务"],
)

@router.get("", summary="列出所有任务", description="从 Claude Code 的 scheduled_tasks.json 同步后返回全部定时任务。")
def list_tasks() -> list[dict]: ...

@router.get("/{task_id}", summary="查看单个任务", description="按 ID 查询单个任务的详细信息。")
def get_task(task_id: str) -> dict: ...
```

### 5.3 Pydantic 模型中文化 (`backend/models/task.py`)

```python
class Task(BaseModel):
    id: str = Field(..., description="任务唯一 ID,由 Claude Code 分配")
    name: str = Field(..., description="任务显示名")
    prompt: str = Field(..., description="任务要执行的 prompt 文本")
    schedule: str = Field(..., description="cron 表达式,例如 '0 9 * * *'")
    enabled: bool = Field(..., description="是否启用")
    created_at: datetime = Field(..., description="创建时间 (ISO 8601)")
    # ... 其余字段同理
```

### 5.4 前端 JS 渲染逻辑

`app.js` 大致结构:

```javascript
const state = { schema: null, health: 'unknown' };

async function init() {
  state.schema = await fetch('/openapi.json').then(r => r.json());
  renderSidebar();
  renderEndpoints();
  startHealthPolling();
}

function renderSidebar() {
  // 按 tag 分组,生成侧边栏链接
  const tags = collectTags(state.schema);
  // ...
}

function renderEndpoints() {
  // 遍历 paths,生成 endpoint 卡片
  for (const [path, methods] of Object.entries(state.schema.paths)) {
    for (const [method, op] of Object.entries(methods)) {
      renderCard(method, path, op);
    }
  }
}

async function tryEndpoint(method, path, params) {
  const url = buildUrl(path, params);
  const res = await fetch(url, { method });
  const body = await res.json().catch(() => res.text());
  return { status: res.status, body };
}

// 启动
init();
```

---

## 六、测试策略

### 6.1 后端测试

**`tests/test_home_page.py`** (新增):
- `test_home_returns_200` — `GET /` 返回 200,Content-Type 含 `text/html`
- `test_home_references_assets` — HTML 包含 `app.css` 和 `app.js` 引用
- `test_assets_served` — `GET /assets/app.css`、`/assets/app.js` 返回 200
- `test_swagger_disabled` — `GET /docs` 返回 404
- `test_redoc_disabled` — `GET /redoc` 返回 404

**`tests/test_chinese_i18n.py`** (新增):
- `test_tags_in_chinese` — `openapi.json` 至少包含 `"服务状态"`、`"定时任务"` 标签
- `test_summary_in_chinese` — 每个 endpoint 的 `summary` 是中文(非空,非纯 ASCII)
- `test_field_descriptions_in_chinese` — `Task` 模型字段的 `description` 是中文

### 6.2 现有测试

- 21 个测试全部保留并通过
- 唯一需要更新的:`test_api_tasks.py` 中如果有断言依赖 `tags=["tasks"]` 字面值,改成 `tags=["定时任务"]`(如有)

### 6.3 手动验证 (用户在浏览器)

启动服务后,访问 `http://127.0.0.1:8765/`,确认:
- 暗色背景、字体清晰
- 3 个 endpoint 卡片全部展示,中文标签
- 点"试一下"能成功调用 `/api/system/status` 和 `/api/tasks`
- 健康指示器绿点 + 时间戳更新
- 缩窄浏览器到手机宽度,布局变为单列

---

## 七、风险与边界

### 7.1 风险

| 风险 | 缓解 |
|------|------|
| 中文路径/JSON 在某些 HTTP 客户端乱码 | FastAPI 默认 UTF-8,经测试 21 个现有测试不受影响 |
| 前端 fetch `/openapi.json` 跨域 | 同源,不触发 CORS |
| 后续 Phase 5 加 Cloudflare Access 后,无 token 无法访问 | 在 home 路由的 `tryEndpoint` 里透传 `Cf-Access-Jwt-Assertion` header(预留,不在本次实现) |
| 浏览器缓存导致改动看不到 | 静态资源加版本号查询参数 `?v=0.1.0` |

### 7.2 边界

- **不改任何业务逻辑** — API 行为、数据库、TaskStore、HistoryStore 一个不动
- **不引入新依赖** — 维持当前 `requirements.txt` 不变
- **代码不删英文注释** — Python docstring 仍保留英文(便于代码搜索/AI 阅读),只动 `tags`、`summary`、`description`、UI 文本

---

## 八、可逆性

- 删除 `backend/static/` 整个目录 → 静态页消失
- 改回 `main.py` 的 `docs_url="/docs"` → Swagger UI 恢复
- 还原 `system.py`、`tasks.py`、`task.py` → OpenAPI 回到英文
- 不修改 `data/mzc.db`,不触碰 Claude Code 文件
- 整体改动 < 500 行,Git revert 单条提交即可

---

## 九、后续工作 (不在本次范围)

- Phase 5:加 Cloudflare Access 鉴权,前端自动透传 JWT
- Phase 8:真正的 Web UI(任务增删改 + 运行历史图表),替换本页
- i18n:加亮色主题、英文切换
- PWA:加 manifest,支持手机"加到主屏幕"
