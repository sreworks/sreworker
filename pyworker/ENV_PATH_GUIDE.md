# .env 文件路径指南

## 📍 核心原则

`.env` 文件的加载路径取决于**当前工作目录（Current Working Directory）**，而不是脚本文件的位置。

## 🔍 代码分析

在 `app/config.py` 中：

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",  # 相对路径
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
```

`env_file=".env"` 是相对路径，pydantic-settings 会从**当前工作目录**查找该文件。

## ✅ 推荐配置

### 标准目录结构

```
sreworker/
├── pyworker/              # 项目根目录
│   ├── .env               # ✅ .env 文件放在这里
│   ├── .env.example       # 配置模板
│   ├── app/               # 应用代码
│   │   ├── main.py
│   │   └── config.py
│   └── requirements.txt
```

### .env 文件位置

```bash
/home/twwyzh/sreworker/pyworker/.env  # ✅ 正确位置
```

## 🚀 启动方式与 .env 路径对应关系

### ✅ 方式 1：推荐方式（从 pyworker 目录启动）

```bash
cd /home/twwyzh/sreworker/pyworker
uvicorn app.main:app --host 0.0.0.0 --port 7788
```

- **工作目录**: `/home/twwyzh/sreworker/pyworker`
- **.env 位置**: `/home/twwyzh/sreworker/pyworker/.env` ✅
- **结果**: 正常加载配置

### ✅ 方式 2：使用 python -m 启动

```bash
cd /home/twwyzh/sreworker/pyworker
python -m app.main
```

- **工作目录**: `/home/twwyzh/sreworker/pyworker`
- **.env 位置**: `/home/twwyzh/sreworker/pyworker/.env` ✅
- **结果**: 正常加载配置

### ⚠️ 方式 3：从父目录启动（不推荐）

```bash
cd /home/twwyzh/sreworker
uvicorn pyworker.app.main:app --host 0.0.0.0 --port 7788
```

- **工作目录**: `/home/twwyzh/sreworker`
- **.env 位置**: `/home/twwyzh/sreworker/.env` ⚠️（不是 pyworker/.env）
- **结果**: 需要在父目录创建 .env 文件

### ❌ 错误示例

```bash
cd /home/twwyzh/sreworker/pyworker/app
python main.py
```

- **工作目录**: `/home/twwyzh/sreworker/pyworker/app`
- **.env 位置**: `/home/twwyzh/sreworker/pyworker/app/.env` ❌
- **结果**: 找不到配置文件

## 🛠️ 快速设置

### 1. 创建 .env 文件

```bash
cd /home/twwyzh/sreworker/pyworker
cp .env.example .env
```

### 2. 编辑配置

```bash
nano .env
# 或
vim .env
```

设置必要的环境变量，例如：

```env
PORT=7788
CLAUDE_API_KEY=your-api-key-here
```

### 3. 验证配置

```bash
# 启动服务，查看启动日志
uvicorn app.main:app --host 0.0.0.0 --port 7788

# 启动时会显示配置信息，检查：
# - API Key (from .env): sk-xxx...xxx ✅
```

## 🔍 验证 .env 是否被加载

### 方法 1：查看启动日志

启动服务时，系统会显示详细配置信息：

```
======================================================================
Starting AI Code Worker Manager...
======================================================================

📡 Server Configuration:
  Host: 0.0.0.0
  Port: 7788                    # 如果显示 7788，说明 .env 生效
  Debug: False

🔵 Claude Code:
  API Key (from .env): sk-xxx...xxx ✅  # 显示这个说明读取成功
```

### 方法 2：使用 Python 测试

```bash
cd /home/twwyzh/sreworker/pyworker
python3 -c "
from app.config import settings
print(f'Port: {settings.port}')
print(f'Debug: {settings.debug}')
print(f'API Key set: {bool(settings.claude_api_key)}')
"
```

### 方法 3：检查当前工作目录

```bash
python3 -c "
import os
print(f'Current directory: {os.getcwd()}')
print(f'.env path: {os.path.join(os.getcwd(), \".env\")}')
print(f'.env exists: {os.path.exists(\".env\")}')
"
```

## 🎯 最佳实践

### ✅ 推荐做法

1. **始终从 pyworker 目录启动**
   ```bash
   cd /home/twwyzh/sreworker/pyworker
   uvicorn app.main:app --host 0.0.0.0 --port 7788
   ```

2. **使用绝对路径（可选）**

   如果需要从任意目录启动，可以修改 `config.py`：
   ```python
   import os
   from pathlib import Path

   BASE_DIR = Path(__file__).resolve().parent.parent

   model_config = SettingsConfigDict(
       env_file=str(BASE_DIR / ".env"),  # 绝对路径
       ...
   )
   ```

3. **使用环境变量（推荐）**

   不依赖 .env 文件，直接使用系统环境变量：
   ```bash
   export ANTHROPIC_API_KEY=your-key-here
   export PORT=7788
   uvicorn app.main:app --host 0.0.0.0 --port 7788
   ```

### ❌ 避免的做法

1. ❌ 不要从其他目录启动服务
2. ❌ 不要把 .env 放在 app/ 目录下
3. ❌ 不要使用多个 .env 文件（除非明确配置）

## 📋 配置优先级

pydantic-settings 的配置加载优先级（从高到低）：

1. **环境变量** (最高优先级)
   ```bash
   export ANTHROPIC_API_KEY=from-env
   ```

2. **.env 文件**
   ```env
   CLAUDE_API_KEY=from-file
   ```

3. **默认值** (最低优先级)
   ```python
   port: int = Field(default=7788)
   ```

示例：
```bash
# 如果同时设置
export PORT=8888           # 环境变量
# .env 文件中: PORT=7788

# 结果：使用 8888 (环境变量优先)
```

## 🆘 常见问题

### Q1: 配置没有生效？

**检查清单：**
- [ ] .env 文件在正确位置（pyworker/.env）
- [ ] 启动命令的工作目录是 pyworker/
- [ ] .env 文件格式正确（KEY=VALUE，无引号）
- [ ] 重启了服务（配置更改后需要重启）

### Q2: 如何确认 .env 文件路径？

```bash
cd /home/twwyzh/sreworker/pyworker
pwd                        # 显示当前目录
ls -la .env               # 检查 .env 是否存在
```

### Q3: 可以使用多个 .env 文件吗？

默认只会加载一个 .env 文件。如果需要多环境配置：

```bash
# 开发环境
cp .env.example .env.dev

# 生产环境
cp .env.example .env.prod

# 启动时指定
ENV_FILE=.env.dev uvicorn app.main:app
```

需要修改代码支持 `ENV_FILE` 环境变量。

## 📞 技术支持

如果遇到配置问题：

1. 查看启动日志中的配置信息
2. 使用验证命令检查工作目录和文件存在性
3. 确认启动命令和工作目录正确

## 总结

**关键点：**
- ✅ .env 文件放在 `pyworker/.env`
- ✅ 从 `pyworker/` 目录启动服务
- ✅ 使用 `cd pyworker && uvicorn app.main:app` 启动
- ✅ 或者直接使用系统环境变量（推荐）
