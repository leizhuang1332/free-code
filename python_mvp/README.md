# Python MVP Session

基于 DeepSeek API 的最小会话执行链路复刻。

## 文件结构

```
python_mvp/
├── pyproject.toml                    # uv 项目管理
├── app/
│   ├── __init__.py
│   ├── messages.py                   # Message, ToolUse, AssistantTurn, 事件
│   ├── model_client.py               # ModelClient protocol, FakeModelClient, DeepSeekOpenAIClient
│   ├── query_loop.py                 # 核心模型循环 (assistant → tool → assistant)
│   ├── tool_registry.py              # Tool protocol, ToolRegistry
│   ├── tool_runner.py                # 串行执行工具 (含权限检查)
│   ├── input_processor.py            # 用户输入处理 (/help, /clear)
│   ├── transcript.py                 # JSONL transcript 记录
│   ├── engine.py                     # SessionEngine (会话引擎)
│   ├── repl.py                       # REPL 入口
│   ├── permissions.py                # 权限模型 (READ_ONLY/ALLOW_ALL/DENY_ALL)
│   └── tools/
│       ├── __init__.py               # create_read_only_registry, create_all_tools_registry
│       ├── path_guard.py             # workspace 路径保护
│       ├── list_dir.py               # 列出目录工具
│       ├── read_file.py              # 读取文件工具 (含大小/UTF-8限制)
│       └── write_file.py             # 写入文件工具 (WRITE 能力)
└── tests/
    ├── test_query_loop.py            # 核心循环测试
    ├── test_tool_runner.py           # 工具执行+权限测试
    ├── test_model_client.py          # DeepSeek client 测试
    ├── test_file_tools.py            # 文件工具测试
    ├── test_builtin_tools.py         # 注册工厂测试
    ├── test_input_processor.py       # 输入处理测试
    ├── test_transcript.py            # transcript 测试
    ├── test_engine.py                # 会话引擎测试
    ├── test_permissions.py           # 权限策略测试
    └── test_write_file_tool.py       # 写文件工具测试
```

## 使用方式

### 依赖管理

项目使用 `uv` 管理依赖：

```bash
cd python_mvp

# 同步依赖
uv sync --dev

# 添加运行时依赖
uv add <package>

# 添加开发依赖
uv add --dev <package>
```

### 运行测试

```bash
# 全部测试
uv run pytest -q

# 单个测试文件
uv run pytest tests/test_query_loop.py -q

# 多个测试文件
uv run pytest tests/test_tool_runner.py tests/test_file_tools.py -q
```

### 启动 REPL

需要设置 `DEEPSEEK_API_KEY` 环境变量：

```bash
export DEEPSEEK_API_KEY=your_key_here
uv run python -m app.repl
```

支持的命令：

- `/help` — 显示帮助
- `/clear` — 清空对话历史
- `/exit` / `exit` / `quit` — 退出 REPL

### 模型配置

| 环境变量 | 默认值 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | — | **必填** |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型名称 |

### 权限策略

REPL 默认使用 `READ_ONLY` 权限模式，只允许 `list_dir` 和 `read_file`，拒绝 `write_file`。可通过代码指定其他模式：

- `PermissionMode.READ_ONLY` — 只读 (默认)
- `PermissionMode.ALLOW_ALL` — 允许所有
- `PermissionMode.DENY_ALL` — 拒绝所有

## Phase 划分

| Phase | 目标 |
|---|---|
| Phase 1 | 用 fake 模型和 echo 工具跑通最小工具调用闭环 |
| Phase 2 | 接入 DeepSeek OpenAI-compatible API |
| Phase 3 | 增加 workspace 限制下的 `list_dir` 和 `read_file` |
| Phase 4 | 增加可交互 REPL、本地命令和 JSONL transcript |
| Phase 5 | 增加默认受限的 `write_file` 和权限策略 |
