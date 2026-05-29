# Python MVP 会话执行链路复刻开发计划索引

本文档把 `docs/Python-MVP-会话执行链路复刻方案.md` 拆分为 5 个可独立验收的 phase。每个 phase 都应在开始前确认上一 phase 的测试通过，并在结束时提交一次小而完整的变更。

## Phase 划分

| Phase | 文档 | 目标 |
|---|---|---|
| Phase 1 | `phase-01-fake-query-loop.md` | 用 fake 模型和 echo 工具跑通最小工具调用闭环。 |
| Phase 2 | `phase-02-real-model-client.md` | 接入真实模型 client，并完成内部消息与 provider 格式转换。 |
| Phase 3 | `phase-03-file-read-tools.md` | 增加 workspace 限制下的 `list_dir` 和 `read_file`。 |
| Phase 4 | `phase-04-repl-transcript.md` | 增加可交互 REPL、本地命令和 JSONL transcript。 |
| Phase 5 | `phase-05-safe-write-tool.md` | 增加默认受限的 `write_file` 和权限策略。 |

## 推荐执行顺序

1. 先执行 Phase 1，保证不用网络也能验证核心链路。
2. Phase 2 接入真实模型，但仍保留 fake client 作为测试基线。
3. Phase 3 扩展只读文件工具，让模型能读取项目上下文。
4. Phase 4 增加人工可用入口和 transcript，形成可演示 MVP。
5. Phase 5 再引入写能力，避免在权限模型稳定前开放高风险工具。

## 统一约定

- Python 包目录：`python_mvp/app/`
- 测试目录：`python_mvp/tests/`
- 依赖管理：必须使用 `uv`，不要用 `pip install` 直接管理项目依赖。
- 初始化/同步依赖：`cd python_mvp && uv sync --dev`
- 添加运行时依赖：`cd python_mvp && uv add <package>`
- 添加开发依赖：`cd python_mvp && uv add --dev <package>`
- 运行测试：`cd python_mvp && uv run pytest -q`
- 运行 REPL：`cd python_mvp && uv run python -m app.repl`
- 模型 provider：使用 DeepSeek 的 OpenAI-compatible API。
- 模型 base URL：`https://api.deepseek.com`
- 默认模型：`deepseek-v4-flash`
- 模型环境变量：`DEEPSEEK_API_KEY` 必填；`DEEPSEEK_BASE_URL` 默认 `https://api.deepseek.com`；`DEEPSEEK_MODEL` 默认 `deepseek-v4-flash`。
- 默认权限：只读优先，写操作必须显式开启。
- 所有 phase 都保留同步实现，后续如需 async 可在接口稳定后演进。

