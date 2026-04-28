# 示例 AI 插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：实例化 `LLMChatService` + `MainWidget`，管理 `StreamWorker` |
| `function/services/llm_chat_service.py` | LLM 接口层：委托 `llm_tools.py` 注册工具 |
| `function/tools/llm_tools.py` | 工具定义（calculate, get_current_time） |
| `ui/main_widget.py` | Provider 选择、聊天输入输出、流式显示 |
| `config/default.json` | 系统提示词与演示消息配置 |

## 核心类
### `LLMChatService`
- `create_conversation(...)`、`send_message(...)`、`stream_send_message(...)`：LLM 交互。
- `register_tools()`、`get_tool_executor()`：Function Calling 工具注册。

### `StreamWorker` (QThread)
- 在独立线程中执行流式请求，通过 Signal 向主线程回传 chunk。

## 关键设计决策
1. 流式聊天使用 `QThread + Signal` 避免阻塞主线程。
2. 工具定义与业务逻辑分离，便于扩展。

## 配置
`config/default.json` 中 `chat.system_prompt` 和 `chat.demo_messages` 定义了默认提示词和演示消息。
