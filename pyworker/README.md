# PyWorker2 API

基于 FastAPI 的 Worker 与 Conversation 管理服务，用于统一管理不同 AI 编程工具（Claude Code、OpenCode 等）的会话交互。

## 技术栈

- **Web 框架**: FastAPI + Uvicorn
- **数据库**: DuckDB（嵌入式 SQL 数据库，文件存储）
- **数据验证**: Pydantic v2
- **测试框架**: pytest + pytest-asyncio + httpx
- **文件监控**: watchfiles（Rust notify 原生 async）
- **其他**: python-dotenv（环境变量）

## 项目结构

```
pyworker/
├── app/
│   ├── main.py                        # FastAPI 应用入口与生命周期管理
│   ├── api/v1/
│   │   ├── workers.py                 # Worker REST API 路由
│   │   └── conversations.py           # Conversation REST API 路由
│   ├── db/
│   │   ├── connection.py              # DuckDB 连接管理与 Schema 初始化
│   │   ├── database_models/           # 数据库模型（dataclass）
│   │   │   ├── worker.py
│   │   │   ├── conversation.py
│   │   │   └── message.py
│   │   └── repositories/             # 数据访问层（CRUD）
│   │       ├── base.py
│   │       ├── worker.py
│   │       ├── conversation.py
│   │       └── message.py
│   ├── models/                        # Pydantic 请求/响应模型
│   │   ├── worker.py
│   │   ├── conversation.py
│   │   └── message.py
│   ├── services/
│   │   ├── conversation_manager.py    # 会话输入文件存储管理
│   │   └── file_manager.py           # 通用文件监控服务
│   ├── workers/                       # Worker 实现层
│   │   ├── __init__.py                # Worker 注册表与默认类型
│   │   └── v1/
│   │       ├── base.py                # 抽象 Worker 基类
│   │       ├── claude.py              # Claude Code CLI 实现
│   │       └── opencode.py            # OpenCode 实现（TODO）
│   └── utils/
│       ├── logger.py                  # 日志工具
│       └── file_reader.py            # 高效文件反向读取工具
├── static/
│   └── index.html                     # 前端 Web UI
├── tests/
│   ├── api/v1/
│   │   ├── conftest.py                # 测试 Fixtures
│   │   ├── test_worker.py             # Worker API 测试
│   │   └── test_conversation.py       # Conversation API 测试
│   └── utils/
│       └── test_file_reader.py        # 文件读取工具测试
├── data/                              # 运行时数据目录
│   ├── pyworker2.db                   # DuckDB 数据库文件
│   └── conversations/                 # JSONL 会话输入/消息文件
└── pytest.ini                         # pytest 配置
```

## 架构设计

### 三层架构

```
API 路由层 (api/v1/)
    ↓
服务层 (services/) + 仓储层 (repositories/)
    ↓
数据层: DuckDB (结构化数据) + JSONL 文件 (会话输入 & 消息)
```

### 依赖注入

路由层通过 FastAPI 的 `Depends()` 模式获取 Repository 实例。数据库连接、ConversationManager 和 FileManager 在应用生命周期（lifespan）中初始化，注入到路由模块。

### Worker 插件机制

通过抽象基类 `BaseWorker` 定义统一接口，不同 AI 工具实现各自的 Worker 子类，并在注册表中注册。Worker 构造函数统一接受 `env_vars`、`command_params` 和 `file_manager` 参数。

## 数据库模型

### workers 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str (PK) | Worker 名称标识符 |
| type | str | Worker 类型（claudecode / opencode） |
| env_vars | JSON | 环境变量键值对 |
| command_params | JSON | 命令行参数列表 |
| created_at | datetime | 创建时间 |

### conversations 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | str (PK) | UUID |
| worker_id | str (FK) | 关联的 Worker |
| project_path | str | 项目目录路径 |
| name | str | 会话名称 |
| created_at | datetime | 创建时间 |
| last_activity | datetime | 最后活动时间 |
| is_current | bool | 是否为当前活跃会话 |
| raw_conversation_id | str (nullable) | 平台特定的会话 ID（如 Claude Code session_id） |
| metadata | JSON | 附加元数据 |

### messages 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | int (PK) | 自增序列生成 |
| conversation_id | str (FK) | 关联的会话 |
| worker_id | str (FK) | 关联的 Worker |
| message_type | str | 消息类型（user / assistant / queue-operation / system） |
| uuid | str (UNIQUE) | 来源唯一标识，用于去重 |
| content | JSON | 消息内容（灵活结构，按类型不同而变化） |
| timestamp | datetime | 消息时间戳 |

### 索引

- `idx_workers_type` — workers(type)
- `idx_conversations_worker` — conversations(worker_id)
- `idx_conversations_project` — conversations(project_path)
- `idx_conversations_current` — conversations(worker_id, is_current)
- `idx_messages_conversation` — messages(conversation_id)
- `idx_messages_worker` — messages(worker_id)
- `idx_messages_timestamp` — messages(timestamp)

## API 接口

### 系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 前端 Web UI |
| GET | `/health` | 健康检查，返回 `{status, version}` |

### Workers (`/api/v1/workers`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/workers` | 列出所有 Worker，支持 `worker_name` 过滤 |
| POST | `/api/v1/workers` | 创建 Worker（名称需匹配 `^[a-zA-Z][a-zA-Z0-9_-]{0,63}$`） |
| GET | `/api/v1/workers/types` | 获取可用 Worker 类型列表与默认类型 |
| GET | `/api/v1/workers/{worker_name}` | 获取指定 Worker 详情 |
| DELETE | `/api/v1/workers/{worker_name}` | 删除 Worker |

### Conversations (`/api/v1/conversations`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/conversations` | 列出会话，支持 `worker_name` 过滤 |
| POST | `/api/v1/conversations` | 创建会话（需指定 worker_name 和 project_path，path 须为已存在目录） |
| GET | `/api/v1/conversations/{id}` | 获取会话详情 |
| PATCH | `/api/v1/conversations/{id}` | 重命名会话 |
| DELETE | `/api/v1/conversations/{id}` | 删除会话（同时删除 DB 记录和 JSONL 文件） |
| GET | `/api/v1/conversations/{id}/inputs` | 获取会话输入记录（支持 `limit` 参数，1-1000） |
| POST | `/api/v1/conversations/{id}` | 向会话添加输入，触发 Worker 执行 |
| GET | `/api/v1/conversations/{id}/messages` | 获取已同步的标准化消息 |
| POST | `/api/v1/conversations/{id}/messages/sync` | 从代码工具侧同步消息 |

## 标准化消息模型

不同代码工具（Claude Code、OpenCode 等）的原始消息被统一转换为标准化格式：

### MessageResponse

```json
{
  "uuid": "消息唯一标识",
  "type": "user | assistant | queue-operation | system",
  "contents": [MessageContent],
  "timestamp": "ISO 8601 时间戳",
  "parent_uuid": "父消息 UUID（可选）",
  "model": "使用的 AI 模型（可选）",
  "usage": {"input_tokens": ..., "output_tokens": ...},
  "error": "错误信息（可选）"
}
```

### MessageContent

```json
{
  "type": "text | tool_use | tool_result | error",
  "content": "文本内容 / tool input JSON / 错误信息",
  "tool_name": "工具名称（仅 tool_use / tool_result）"
}
```

## Worker 实现

### 抽象接口 (BaseWorker)

所有 Worker 需实现以下方法：

- `start_conversation(path, message)` — 启动新会话，返回 raw_conversation_id
- `continue_conversation(raw_conversation_id, path, message)` — 继续已有会话
- `achieve_conversation(raw_conversation_id)` — 归档/终结会话
- `sync_messages(raw_conversation_id)` — 从远程同步消息，返回标准化 `List[MessageResponse]`

构造函数签名：`__init__(env_vars, command_params, file_manager)`

### ClaudeCodeWorker（已实现）

封装 Claude Code CLI 工具：

- 通过异步子进程调用 `claude` 命令
- 启动会话：`claude --print --output-format json {message}`
- 继续会话：`claude --print --output-format json --resume {session_id} {message}`
- 消息同步：从 `~/.claude/projects/{project_dir}/{session_id}.jsonl` 读取会话记录，转换为标准化 `MessageResponse`
- 支持自定义环境变量和命令行参数
- 在指定的 project_path 工作目录中运行
- **文件监控**：通过 FileManager 监控 `~/.claude/projects/` 目录，活跃 session 的 JSONL 文件变更时自动触发消息同步

#### Session 激活机制

ClaudeCodeWorker 使用类级别状态管理活跃 session：

- `activate_session(raw_conversation_id)` — 将 session 加入监控集合
- `deactivate_session(raw_conversation_id)` — 从监控集合移除
- `start_watching(file_manager)` — 启动目录监控（幂等，首次实例化自动调用）
- `stop_watching()` — 清理监控状态（应用关闭时调用）

### OpenCodeWorker（待实现）

所有方法当前抛出 `NotImplementedError`。

### Worker 注册表

```python
handlers = {
    "claudecode": ClaudeCodeWorker,
    "opencode": OpenCodeWorker,
}
default = "claudecode"
```

## 文件监控服务 (FileManager)

基于 `watchfiles`（Rust notify 库，原生 async）的通用文件监控服务：

- **文件级监控**：`watch(file_path, callback)` / `unwatch(file_path)` — 监控特定文件变更
- **目录级监控**：`watch_directory(dir_path, callback)` / `unwatch_directory(dir_path)` — 递归监控整个目录
- 回调签名：`Callable[[Path], Awaitable[None]]`
- 自动管理 watch loop 的生命周期，无监控对象时自动取消 task
- 在应用 lifespan 中 `start()` / `stop()`

## 双存储系统

### DuckDB（结构化数据）

存储 Worker、Conversation、Message 的元数据和关系。连接时自动初始化 Schema，支持迁移（ALTER TABLE IF NOT EXISTS）。

### JSONL 文件（会话输入 & 消息）

- 输入文件路径：`data/conversations/{worker_name}/{uuid[:2]}/{conversation_id}.input.jsonl`
- 消息文件路径：`data/conversations/{worker_name}/{uuid[:2]}/{conversation_id}.messages.jsonl`

**输入文件**：每行一条 JSON 记录，包含 role、content、timestamp、metadata。

**消息文件**：存储标准化 `MessageResponse` 列表，由 `sync_messages` 全量覆写。

ConversationManager 支持高效的反向读取（从文件末尾按块读取），适合大文件场景。

## 会话生命周期

1. **创建会话** → 在 DB 中生成记录，`raw_conversation_id` 为空
2. **首次输入** → 调用 `worker.start_conversation()` → 获取 `raw_conversation_id` 并回写 DB → 激活 session 监控
3. **后续输入** → 调用 `worker.continue_conversation(raw_conversation_id, ...)`
4. **手动同步** → 调用 `POST /messages/sync` → `worker.sync_messages()` → 标准化消息存入 JSONL
5. **自动同步** → FileManager 检测到活跃 session 的 JSONL 文件变更 → 自动触发 `sync_messages`

## 前端 UI

内置简单的 Web 界面（`static/index.html`），通过 `GET /` 访问：

- 三栏布局：Workers | Conversations | Chat
- 创建 Worker（支持自定义环境变量和命令参数）
- 创建和管理 Conversation
- 发送消息并自动同步回复
- 10 秒轮询更新消息
- 暗色主题，原生 JavaScript 实现

## 运行

```bash
# 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 7788

# 运行测试
pytest
```

服务启动后：
- Web UI：`http://localhost:7788/`
- Swagger 文档：`http://localhost:7788/docs`
- 健康检查：`http://localhost:7788/health`
