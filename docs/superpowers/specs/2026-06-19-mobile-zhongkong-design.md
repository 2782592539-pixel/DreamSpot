# 家用 Claude Code 移动中控 (MZC) - 设计文档

> 日期:2026-06-19
> 作者:H-yue (与 Claude Code 协作)
> 状态:设计待复核

---

## 一、项目目标

让用户能用**手机**远程查看、触发和管理家用 Windows 笔记本上的 **Claude Code 任务**(包括 CronCreate 创建的定时任务),并在 **飞书 App** 中接收任务运行通知,实现"人在外面,家里电脑在跑 Claude Code"的体验。

### 核心需求

| # | 需求 | 优先级 |
|---|------|--------|
| 1 | 完整手机中控(查看任务、结果、调起 Claude Code 交互、查看会话历史) | P0 |
| 2 | 公网随时访问(出差、路上都能用) | P0 |
| 3 | 飞书 App 集成(通知 + 卡片按钮 + 跳转) | P0 |
| 4 | 定时任务来源:Claude Code CronCreate(`durable=true`) | P0 |
| 5 | 运行环境:家用 Windows 11 笔记本(会休眠) | P0 |
| 6 | 数据安全:Cloudflare Access + 飞书签名校验 | P0 |
| 7 | 零成本:全部使用免费工具 | P1 |
| 8 | 会话级任务(`durable=false`)同步 - 暂不做,后期升级 | P2 |

### 非目标 (YAGNI)

- 多用户权限管理(只用自己)
- 集群管理(只一台电脑)
- 移动端原生 App(先用 Web 响应式)
- 公开给别人用
- 实时流式 token 输出(走异步轮询)

---

## 二、顶层架构

### 2.1 五层架构

| 层 | 组件 | 作用 |
|----|------|------|
| L1 | 操作系统 | Windows 11 + 电源管理 + 任务计划程序 |
| L2 | Claude Code | CLI + 守护进程 + CronCreate |
| L3 | 中控服务 (Python) | Web API、任务调度、飞书推送、SQLite |
| L4 | 穿透层 | Cloudflare Tunnel + Cloudflare Access |
| L5 | 客户端 | 手机浏览器 (Web) + 飞书 App |

### 2.2 架构图

```
[安卓手机]
   ├─ 飞书 App (主入口:通知 + 卡片按钮 + 跳转链接)
   └─ 浏览器 (深度操作:完整会话 / 长结果)
        ↓ 通过 Cloudflare Access 登录
[Cloudflare 边缘 → Cloudflare Access 鉴权]
        ↓ 放行后
[Cloudflare Tunnel]
        ↓
[家用 Win11]
   ├─ cloudflared (Tunnel 客户端)
   └─ 中控服务 FastAPI (127.0.0.1:8765)
        ├─ CF Access JWT 二次校验
        ├─ 任务管理 API
        ├─ Claude Code 包装
        ├─ 飞书推送
        └─ SQLite (运行历史)
   ├─ Claude Code 守护进程 (NSSM)
   └─ .claude/scheduled_tasks.json
```

### 2.3 关键约束

- Claude Code 进程由 NSSM 拉起,挂掉自动重启
- 中控服务和 Claude Code 在同一台机器,通过本地 HTTP/CLI 通信
- 穿透层只暴露中控服务的 Web 端口,**不直接暴露 Claude Code**
- 所有外部请求经 Cloudflare → 中控服务;中控可主动调飞书 API,飞书事件通过 webhook 回调进中控

---

## 三、模块职责

### 3.1 M1. 电源管理与开机自启

**职责**:确保电脑能被远程"叫醒",且服务始终在跑。

| 子组件 | 做什么 | 实现方式 |
|--------|--------|----------|
| 禁休眠 | 关闭自动休眠,保留用户手动休眠 | `powercfg /change standby-timeout-ac 0` |
| 唤醒触发器 | 凌晨定时唤醒做备份 | Windows 任务计划程序,设"唤醒计算机" |
| 中控服务自启 | 用户登录后自动启动 | NSSM 注册 Windows 服务,启动类型"自动" |
| cloudflared 自启 | 同上 | 单独注册 NSSM 服务 |
| 崩溃自重启 | 进程死了自动拉起 | NSSM 自带,默认开启 |

**关键文件位置**:
```
C:\Users\27825\Desktop\First_cc\
├─ scripts\
│   ├─ install_services.bat     # 一键注册 NSSM 服务
│   ├─ disable_sleep.ps1        # 禁休眠脚本
│   └─ uninstall_services.bat   # 反向清理
```

**为什么用 NSSM 而不是 Task Scheduler?**
- Task Scheduler 启动的进程会绑定到用户会话,会话注销就死
- NSSM 注册的是真正的 Windows 服务,与会话无关

### 3.2 M2. 中控服务 (FastAPI)

**职责**:系统的"大脑",对外暴露 HTTP API,对内协调 Claude Code 和飞书。

**目录结构**:
```
backend/
├─ main.py                  # FastAPI 入口,挂载路由
├─ config.py                # 配置(读 .env)
├─ auth/
│   ├─ cloudflare_access.py # 校验 CF Access 传下来的 JWT
│   └─ feishu_signature.py  # 校验飞书 webhook 签名
├─ api/
│   ├─ tasks.py             # /tasks CRUD
│   ├─ sessions.py          # /sessions 查询 Claude Code 会话
│   ├─ chat.py              # /chat 转发到 Claude Code
│   └─ system.py            # /system 状态、心跳
├─ services/
│   ├─ scheduler.py         # APScheduler,加载/触发 cron
│   ├─ claude_runner.py     # 包装 claude CLI 调用
│   ├─ feishu_client.py     # 飞书消息发送 + 卡片
│   ├─ task_store.py        # 读写 .claude/scheduled_tasks.json
│   └─ history_store.py     # SQLite,存运行历史
└─ models/
    ├─ task.py              # Pydantic 数据模型
    └─ run_record.py
```

**核心 API 列表**:

| 方法 | 路径 | 作用 |
|------|------|------|
| GET | `/api/tasks` | 列出所有定时任务 |
| GET | `/api/tasks/{id}` | 任务详情 |
| POST | `/api/tasks/{id}/run` | 手动触发一次 |
| POST | `/api/tasks/{id}/pause` | 暂停/恢复 |
| GET | `/api/sessions` | Claude Code 会话列表 |
| GET | `/api/sessions/{id}/messages` | 会话历史 |
| POST | `/api/chat` | 发起新会话或继续会话 |
| GET | `/api/system/status` | 服务健康 + Claude Code 状态 |
| POST | `/feishu/webhook` | 飞书事件回调入口 |

### 3.3 M3. Claude Code 守护与调度

**职责**:让 Claude Code 始终可用,且能执行 CronCreate 创建的任务。

#### 3.3.1 Claude Code 不是 daemon

Claude Code CLI 默认是交互式 TUI,不是后台服务。两种用法:

| 场景 | 触发方式 | 实现 |
|------|----------|------|
| 定时任务(无人值守) | 后台触发 | `claude -p "任务prompt" --output-format json` 一次性调用 |
| 用户手动聊天 | 用户交互 | 中控服务起 claude 进程,维护会话 ID,stdin/stdout 通信 |

#### 3.3.2 CronCreate 任务处理(方案 α:只接管 durable=true)

**核心决策**:中控服务**自己解析** `~/.claude/scheduled_tasks.json`,用自己的 APScheduler 重新调度,触发时调 `claude -p`,自己捕获结果 → 推飞书。

**理由**:
- 简单可靠,APScheduler 是工业级方案
- `durable=false` 的"会话级"任务按用户预期会消失,不接管
- 鼓励用户把"重要任务"设为 `durable=true`,由本项目统一管理

**会话级任务同步问题**(已知限制):
- `durable=false` 任务只存在 Claude Code 进程内存,无对外接口
- 现状不同步,后期可升级到方案 β (Hook 同步) 或方案 γ (中控代理 CronCreate)
- 临时任务用户接受"在 Claude Code 里手动看"

#### 3.3.3 会话存储

Claude Code 自己的会话历史存在 `~/.claude/projects/<encoded-path>/<session-id>.jsonl`。中控服务**只读不写**,直接读取这些文件呈现给手机端。

---

## 四、核心数据流

### 4.1 流程 ① 手机查看定时任务列表

```
[手机浏览器]                          [中控服务]                [Claude Code]
    │                                      │                          │
    │  GET https://xxx.trycloudflare.com/  │                          │
    │  /api/tasks                           │                          │
    │  (带 CF Access JWT cookie)            │                          │
    ├──────────────────────────────────────►│                          │
    │                                      │ 1. 校验 JWT              │
    │                                      │ 2. 读 ~/.claude/         │
    │                                      │    scheduled_tasks.json  │
    │                                      │ 3. 与 SQLite 中的        │
    │                                      │    enabled/disabled 状态 │
    │                                      │    合并                  │
    │  200 OK [                            │                          │
    │    {id, name, cron, next_run,        │                          │
    │     last_run, status},               │                          │
    │    ...                               │                          │
    │  ]                                   │                          │
    │◄──────────────────────────────────────┤                          │
```

### 4.2 流程 ② 在 Web 创建新定时任务

```
[手机浏览器]                  [中控服务]                  [Claude Code]              [飞书]
    │                              │                          │                       │
    │ POST /api/tasks              │                          │                       │
    │ {name, cron, prompt}         │                          │                       │
    ├─────────────────────────────►│                          │                       │
    │                              │ 1. 写 SQLite (status=enabled)                  │
    │                              │ 2. 调 claude CLI 创建 durable 任务:           │
    │                              │    claude /cron durable=true "..."             │
    │                              ├─────────────────────────►│                       │
    │                              │                          │ 3. 写 JSON 文件       │
    │                              │                          │ 4. 注册内部调度器     │
    │                              │◄─────────────────────────┤                       │
    │                              │ 5. 推飞书消息:                                  │
    │                              │    "✅ 任务已创建: 每天9点日报"                │
    │                              ├───────────────────────────────────────────────►│
    │  201 Created                 │                                                  │
    │◄─────────────────────────────┤                                                  │
```

### 4.3 流程 ③ 定时任务自动触发(核心)

```
[APScheduler]            [中控服务]              [Claude Code]            [飞书]         [SQLite]
    │                        │                       │                      │             │
    │ tick! 触发时间到        │                       │                      │             │
    ├───────────────────────►│                       │                      │             │
    │                        │ 1. 先在 JSON 中       │                      │             │
    │                        │    last_run 字段写     │                      │             │
    │                        │    (防 Claude 重复触发)│                      │             │
    │                        │ 2. 调 claude -p       │                      │             │
    │                        │    "任务prompt"        │                      │             │
    │                        │    --output-format json│                      │             │
    │                        ├──────────────────────►│                      │             │
    │                        │                       │ 3. 执行任务          │             │
    │                        │                       │    (可能 1-5 分钟)   │             │
    │                        │◄──────────────────────┤                      │             │
    │                        │ 4. 解析 JSON 输出     │                      │             │
    │                        │ 5. 写 SQLite run 记录 │                      │             │
    │                        ├──────────────────────────────────────────────────────────►│
    │                        │ 6. 推飞书卡片:                                 │             │
    │                        │    标题: ✅/❌ 任务名                            │             │
    │                        │    摘要: 执行结果前 200 字                       │             │
    │                        │    按钮: [查看详情] [再次执行]                   │             │
    │                        ├──────────────────────────────────────────────►│             │
```

**防双触发策略**(方案 A - 推荐先用):
- 中控服务抢先触发后,在 `scheduled_tasks.json` 中改写 `last_run` 字段
- Claude Code 看到 `last_run` 很新(< 任务周期),会跳过本次触发
- **如果 Claude Code 不尊重 `last_run`,切换到方案 B**(中控服务改写为中控自己的格式,Claude Code 看到空 JSON 不触发)

### 4.4 流程 ④ 飞书卡片按钮回调(交互入口)

```
[飞书]                  [Cloudflare]            [中控服务]              [Claude Code]
    │                       │                       │                       │
    │ 用户点 [查看详情]      │                       │                       │
    ├──────────────────────►│                       │                       │
    │ POST /feishu/webhook  │                       │                       │
    │ (带签名 + token)      │                       │                       │
    │                       ├──────────────────────►│                       │
    │                       │                       │ 1. 校验签名           │
    │                       │                       │ 2. 查 SQLite         │
    │                       │                       │ 3. 生成详情卡片       │
    │ 响应卡片(交互更新)    │                       │                       │
    │◄──────────────────────┼───────────────────────┤                       │
    │                       │                       │                       │
    │ 用户点 [再次执行]      │                       │                       │
    ├──────────────────────►│                       │                       │
    │                       ├──────────────────────►│                       │
    │                       │                       │ 触发 claude -p        │
    │                       │                       ├──────────────────────►│
```

---

## 五、数据模型

### 5.1 存储分布

| 存储 | 存什么 | 谁写 | 谁读 |
|------|--------|------|------|
| `scheduled_tasks.json` | Claude Code 自己的任务定义 | Claude Code (创建/删除) | 中控服务 (读+改 last_run) |
| `~/.claude/projects/.../*.jsonl` | Claude Code 会话历史 | Claude Code | 中控服务 (只读) |
| `mzc.db` (SQLite) | 中控服务自己的状态 | 中控服务 | 中控服务 |
| `mzc.log` | 运行日志 | 中控服务 | 人看 / 排查 |

> "mzc" = **M**obile **Z**hong-**C**ontrol 的拼音首字母

### 5.2 `scheduled_tasks.json` 字段(沿用 Claude Code 格式)

只读不写结构,但需要解析关键字段:

```json
{
  "version": 1,
  "tasks": [
    {
      "id": "t_abc123",
      "name": "每天 9 点生成日报",
      "prompt": "读取 ~/work/standup.md,生成昨日完成/今日计划/阻塞项,推送到飞书",
      "schedule": "0 9 * * *",
      "enabled": true,
      "created_at": "2026-06-19T08:30:00Z",
      "last_run": "2026-06-19T09:00:12Z",
      "last_status": "success"
    }
  ]
}
```

**中控服务做的事**:
- 启动时加载,转成内存对象
- 触发时:写 `last_run` 和 `last_status`
- 不创建、不删除(创建走流程 ②,删除由用户在 Claude Code 里操作)

### 5.3 SQLite 表结构 (5 张表)

```sql
-- 任务扩展信息(从 JSON 同步过来,加额外字段)
CREATE TABLE tasks (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    prompt          TEXT NOT NULL,
    schedule        TEXT NOT NULL,
    enabled         INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    created_by      TEXT,
    tags            TEXT,                     -- JSON 数组,用于分组
    next_run_at     TEXT,
    synced_at       TEXT NOT NULL,
    UNIQUE(id)
);

-- 每次运行记录(完整 output 存储)
CREATE TABLE runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id         TEXT NOT NULL,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL,            -- 'running' | 'success' | 'failed' | 'timeout'
    exit_code       INTEGER,
    output          TEXT,                     -- claude -p 的完整输出
    output_summary  TEXT,                     -- 前 500 字
    duration_sec    INTEGER,
    trigger_source  TEXT NOT NULL,            -- 'cron' | 'manual_web' | 'manual_feishu'
    feishu_msg_id   TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);
CREATE INDEX idx_runs_task_id ON runs(task_id);
CREATE INDEX idx_runs_started_at ON runs(started_at);

-- Claude Code 会话(从 JSONL 文件解析)
CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,
    project_path    TEXT NOT NULL,
    title           TEXT,
    first_message   TEXT,
    message_count   INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    last_active_at  TEXT NOT NULL,
    is_pinned       INTEGER DEFAULT 0
);

-- 用户(目前只有你自己,但留好扩展)
CREATE TABLE users (
    id              TEXT PRIMARY KEY,
    name            TEXT,
    feishu_token    TEXT,
    created_at      TEXT NOT NULL,
    last_seen_at    TEXT
);

-- 操作审计
CREATE TABLE audit_log (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       TEXT NOT NULL,
    user_id         TEXT,
    action          TEXT NOT NULL,
    target          TEXT,
    details         TEXT,                     -- JSON
    ip              TEXT
);
```

### 5.4 数据生命周期

| 事件 | 涉及存储 | 写入动作 |
|------|----------|----------|
| Web 创建任务 | JSON + SQLite + 飞书 | `scheduled_tasks.json` 写新任务;`tasks` 表 insert;飞书推送 |
| APScheduler 触发 | JSON + SQLite + 飞书 | 改 `last_run`;`runs` 表 insert;`feishu_msg_id` 记录 |
| 飞书"再次执行" | SQLite + 飞书 | `runs` 表 insert;飞书推送结果 |
| Web 看会话历史 | SQLite + JSONL(读) | `sessions` 表 lazy 解析 |
| Claude Code 进程重启 | SQLite(无变化) | 中控服务 reload `scheduled_tasks.json` |

### 5.5 关键设计决策

| 决策 | 理由 |
|------|------|
| 用 SQLite 不用 PostgreSQL | 单机、单用户、零运维;SQLite 性能足够 |
| `tasks` 表做 JSON 的"镜像"而不是"主存" | Claude Code 才是任务定义的真相源,中控只是同步 |
| `runs` 表存完整 output | 后期做趋势分析、错误聚合,不用再翻日志 |
| 会话历史存 SQLite 而不是直接读 JSONL | 解析慢、有格式风险;做一次 lazy 缓存 |
| 加 `audit_log` 表 | 出问题排查,记录"谁在什么时间做了什么" |
| `tasks.tags` 字段(用户确认要) | 任务分类,如"日报"/"备份"/"监控" |

---

## 六、错误处理

### 6.1 可自愈的异常(系统自己搞定)

| 场景 | 检测 | 恢复策略 | 告警 |
|------|------|----------|------|
| Claude Code 进程挂掉 | NSSM 探活,或 `claude --version` 退出码非 0 | NSSM 自动拉起,最多重试 3 次,间隔 10 秒 | 飞书推送"⚠️ CC 挂了,已自动恢复" |
| 中控服务自己挂掉 | NSSM 探活,FastAPI `/api/system/status` 不响应 | NSSM 自动拉起 | 飞书推送"⚠️ 中控挂了,已自动恢复" |
| cloudflared 断开 | cloudflared 自身 reconnect 机制 | 自动重连 Cloudflare 边缘 | 飞书推送"⚠️ 隧道断了" |
| `claude -p` 偶发失败 | 退出码非 0,或输出解析失败 | 重试 2 次,间隔 30 秒 | 失败 3 次推飞书"❌ 任务失败:xxx" |
| SQLite 锁等待 | 捕获 `OperationalError: database is locked` | 重试 3 次,指数退避 | 静默(不影响用户) |
| Cloudflare 5xx 转发错误 | FastAPI 捕获非 200 | 5xx 自动重试,4xx 不重试 | 持续 5 分钟 5xx 推飞书 |

### 6.2 可降级的异常(部分功能失效)

| 场景 | 降级行为 | 用户体验 |
|------|----------|----------|
| Cloudflare Tunnel 断了 | 中控服务正常运行,只是外网访问不到 | 手机打不开,电脑还能用;飞书推送断了 |
| 飞书 API 限流(429) | 消息排队,本地暂存到 `outbox` 表,每 30 秒重试 | 延迟收到通知,不丢 |
| Claude Code 进程挂掉 | 定时任务全暂停(中控不调 `claude -p`) | Web 显示"CC 离线",所有任务标红 |
| `claude -p` 输出过大(>10MB) | 截断到 10MB 存 SQLite,完整内容写到 `~/.claude/projects/.../run_xxx.log` | 详情页提示"日志已截断" |
| `scheduled_tasks.json` 损坏 | 中控服务启动失败,显示明确错误 | 飞书推"🚨 JSON 文件损坏,人工修复" |
| CF Access 服务挂了 | Cloudflare 自己的,概率极低 | 暂时禁用 CF Access 鉴权,只靠中控服务 token(降级) |
| 电脑休眠唤醒后 | 重新跑开机自检流程 | 唤醒后 1 分钟内恢复所有功能 |

### 6.3 致命的异常(必须人工介入)

| 场景 | 表现 | 你要做什么 |
|------|------|------------|
| `scheduled_tasks.json` 被 Claude Code 升级改了格式 | 中控解析失败,启动崩溃 | 升级中控服务,适配新格式 |
| NSSM 服务注册信息丢失(系统重装) | 中控服务、CC 都不自启 | 跑 `install_services.bat` 重新注册 |
| 飞书自建应用被禁用/Token 失效 | 所有飞书推送失败,webhook 拒绝 | 重新授权飞书,更新 `.env` 里的 token |
| Cloudflare 账号被封 | Tunnel 整体不可用 | 切换到 Tailscale 备选 |
| 电脑硬盘损坏 | SQLite 和 JSON 都丢 | 恢复备份 |
| cloudflared token 泄露 | 别人可能拿到你的 URL | 撤销 token,重新生成 |

### 6.4 关键设计参数(已确认)

| 参数 | 值 | 理由 |
|------|-----|------|
| `claude -p` 超时阈值 | 10 分钟 | 平衡耐心和资源 |
| 失败重试次数 | 2 次 | 避免无限循环 |
| SQLite output 截断 | 1MB | 防止单条记录撑爆数据库 |
| 自动重启电脑 | ❌ 不重启 | 可能破坏正在进行的 Claude Code 会话 |
| 健康检查频率 | 30 秒 | 平衡实时性和资源消耗 |
| 致命错误是否重启电脑 | ❌ 否 | 同上 |

### 6.5 错误处理核心原则

| 原则 | 体现 |
|------|------|
| 失败要可见 | 所有异常都推飞书,不在日志里"悄悄死" |
| 可恢复的自动恢复 | NSSM 守护、重试机制、指数退避 |
| 不可恢复的立刻告警 | 致命错误红色通道 |
| 降级而非崩溃 | Cloudflare 断了中控服务还能跑,只是外网访问不到 |
| 审计可追溯 | `audit_log` 表记所有操作 |

---

## 七、部署与运维

### 7.1 一键安装流程

**前置条件**:
- [ ] Windows 11 已激活
- [ ] Python 3.11+ 已装
- [ ] Cloudflare 账号已注册
- [ ] 飞书自建应用已创建(拿到 App ID + App Secret)
- [ ] Claude Code 已装好且能跑 `claude -p "hello"`

**安装步骤**:

```powershell
# 1. 进入项目目录
cd C:\Users\27825\Desktop\First_cc

# 2. 装依赖
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. 复制环境变量模板并填写
copy .env.example .env
notepad .env

# 4. 初始化数据库
python -m backend.db.init_db

# 5. 注册 Windows 服务
.\scripts\install_services.bat

# 6. 启动 Cloudflare Tunnel
cloudflared tunnel login
cloudflared tunnel create mzc-tunnel
cloudflared tunnel route dns mzc.yourdomain.com mzc-tunnel  # 可选:绑域名

# 7. 配置 Cloudflare Access
# Cloudflare Dashboard → Zero Trust → Access → Applications
# 加 Self-hosted,绑 mzc.yourdomain.com,Policy: Allow your email

# 8. 验证
curl http://127.0.0.1:8765/api/system/status
# 浏览器访问 https://mzc.yourdomain.com
```

**预期时间**:第一次 2-3 小时。

### 7.2 升级流程

| 升级内容 | 操作 |
|----------|------|
| 中控服务代码 | `git pull` → `nssm restart MzcControl` |
| 依赖包 | `pip install -U -r requirements.txt` → 重启服务 |
| Claude Code | 按官方流程升级;升级后跑 `python -m backend.smoke_test` |
| Cloudflare Tunnel | `cloudflared update` 自动 |
| 数据库 schema | 启动时自动跑 migration;有破坏性变更会先备份再升级 |

### 7.3 备份策略

| 数据 | 频率 | 保留 | 方式 |
|------|------|------|------|
| `mzc.db` (SQLite) | 每天凌晨 3 点 | 30 天 | `scripts/backup_db.ps1` 复制到 `D:\backups\mzc\YYYY-MM-DD.db` |
| `scheduled_tasks.json` | 每次写入前 | 10 个版本 | 中控服务自动加时间戳备份 |
| `~/.claude/projects/**/*.jsonl` | 不备份 | - | 用 OneDrive 自动同步 |
| `.env` | **不备份** | - | 单独存到密码管理器 |
| `requirements.txt` | 跟着 git | 永久 | git 本身 |

### 7.4 日常运维命令速查

```powershell
# 服务状态
nssm status MzcControl
nssm status MzcTunnel

# 启停
nssm start MzcControl
nssm stop MzcControl
nssm restart MzcControl

# 日志(tail -f 等价)
Get-Content C:\Users\27825\Desktop\First_cc\logs\mzc.log -Wait

# 健康检查
curl http://127.0.0.1:8765/api/system/status

# 查看定时任务(JSON 原始)
cat $env:USERPROFILE\.claude\scheduled_tasks.json | python -m json.tool

# 手动触发
curl -X POST http://127.0.0.1:8765/api/tasks/t_abc123/run

# 升级
git pull
.venv\Scripts\pip install -U -r requirements.txt
nssm restart MzcControl
```

### 7.5 故障排查手册

| 症状 | 可能原因 | 排查步骤 |
|------|----------|----------|
| 手机打不开 Web | CF Access / Tunnel / 中控 | `nssm status` → `logs\mzc.log` → `curl 127.0.0.1:8765/api/system/status` |
| 定时任务没触发 | APScheduler / JSON 错 / 电脑休眠 | 看日志 "scheduler started" → `python -c "import json; print(json.load(open(...)))"` → `powercfg /q` |
| 飞书没收到推送 | Token 失效 / API 限流 / webhook URL 错 | 飞书后台 → 应用状态 → 查 `outbox` 表 → `.env` 里的 `FEISHU_WEBHOOK_URL` |
| `claude -p` 报 401 | Claude Code 未登录 | 终端跑 `claude login` |
| cloudflared 一直 reconnect | token 错 / 账号被封 | `cloudflared tunnel info mzc-tunnel` → Cloudflare Dashboard |
| SQLite 损坏 | 突然断电 | 停服务 → `sqlite3 mzc.db ".recover"` → 不行从备份恢复 |
| 电脑休眠后中控不响应 | 休眠后服务没起 | NSSM 唤醒设置 → cloudflared 日志 |
| 中控服务启动失败 | 看错误日志 | `Get-Content logs\mzc.log -Tail 50` |

### 7.6 安全清单

- [ ] `.env` 在 `.gitignore` 里,不提交
- [ ] 飞书 webhook 校验签名(代码里默认开)
- [ ] 中控服务只监听 `127.0.0.1`,不暴露到局域网
- [ ] Cloudflare Access 配了"只允许我的邮箱"
- [ ] `scheduled_tasks.json` 不含敏感 token
- [ ] 备份目录 `D:\backups\mzc\` 不在同步盘里
- [ ] NSSM 服务以当前用户身份运行,不是 SYSTEM
- [ ] cloudflared token 不在公开仓库
- [ ] 飞书自建应用"权限"最小化(只给 `im:message`)
- [ ] 定期换飞书 App Secret(每 90 天)

### 7.7 升级路径(未来)

| 版本 | 新增能力 | 工作量 |
|------|----------|--------|
| v0.1 (当前) | 任务查看 + 飞书推送 + Web 中控 | 基线 |
| v0.2 | 会话级任务同步(方案 β 或 γ) | 1 周 |
| v0.3 | 多用户 + 权限分级 | 1 周 |
| v0.4 | 接入 Gmail / Slack | 1 周 |
| v0.5 | 移动端 PWA | 2-3 周 |
| v1.0 | 多 Claude Code 节点管理 | 2 周 |

---

## 八、待定项 (Open Questions)

1. **防双触发**:方案 A (改 `last_run`) 是否被 Claude Code 尊重?需要跑通后验证。
2. **Claude Code 内部 API**:未来是否会有官方"任务查询"接口?关注 Anthropic 公告。
3. **Tailscale 备选**:Cloudflare Access 出问题时是否切换?需要 Tailscale 账号先开好备用。

---

## 九、参考资料

- Claude Code 官方文档:https://docs.claude.com/en/docs/claude-code
- Cloudflare Tunnel 文档:https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Cloudflare Access:https://developers.cloudflare.com/cloudflare-one/policies/access/
- 飞书开放平台:https://open.feishu.cn/document/server-docs/im-v1/message-events
- NSSM:https://nssm.cc/
- APScheduler:https://apscheduler.readthedocs.io/

---

*文档版本:v0.1 · 创建于 2026-06-19*
