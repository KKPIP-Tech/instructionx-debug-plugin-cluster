# LLM Chat 插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：创建 Service 与 MainWidget 并接线、注册 DataProvider 命名空间 |
| `ui/main_widget.py` | MainWidget：多区域 UI（配置、参数、对话、历史）、事件处理、键盘事件处理（InstructionX_UIKit 组件） |
| `ui/chat_worker.py` | ChatWorker（QThread）：工作线程消费流式生成器，经 Signal 回投 UI |
| `function/services/core_service.py` | LLMChatService：封装 LLM 调用、流式 callback 契约适配、错误分类、图片 base64 转换、偏好持久化 |
| `config/default.json` | 默认温度、Max Tokens 选项、默认插件 ID 配置 |

## 核心类
### `LLMChatService`
- `get_providers()` / `get_models(provider)`：获取可用 Provider 和模型列表。
- `send_message(...)`：同步聊天，分类捕获 LLM 异常（AuthenticationError、RateLimitError 等）。
- `stream_send_message(...)`：流式聊天生成器，yield chunk；内部将框架 `LLMProvider.stream_chat` 的 callback 契约（callback 推块 + 返回完整文本）经「内部线程 + 事件队列」适配为生成器。
- `validate_provider(provider)`：验证 Provider 配置有效性。
- `load_image_as_base64(path)`：图片文件转 base64。
- `save_preference(key, value)` / `load_preference(key)`：偏好设置持久化。
- `save_chat_history(history)` / `load_chat_history()`：对话历史持久化。

### `ChatWorker` (QThread)
- 在后台线程中调用 `stream_send_message()`。
- `chunk_received` Signal：逐段回传文本到 UI。
- `finished` Signal：聊天结束时传递完整结果或错误信息。
- `cancel()`：设置取消标志，优雅中断流式请求。

## 关键设计决策
1. **错误分类**：将 LLM 异常映射为 `error_type`（authentication/rate_limit/timeout/connection/configuration/api/unknown），UI 根据类型给出针对性提示。
2. **线程安全**：`ChatWorker` 继承 `QThread`，通过 Signal 与主线程通信。
3. **Provider 选择**：下拉框在控件创建时填充一次（恢复上次选择），「刷新模型」按钮手动刷新；默认全局配置经 `get_llm_plugin_service().get_default_provider_id(feature="chat")` 查询（框架已不再写系统级数据键）。
4. **Enter 发送**：重写 `keyPressEvent`，Enter 发送消息，Shift+Enter 换行。

## 配置
`config/default.json` 中：
- `llm.default_temperature`: 默认温度（0.7）
- `llm.temperature_slider_range`: 温度滑块范围 [0, 100]
- `llm.max_tokens_options`: Max Tokens 下拉选项 [256, 512, 1024, 2048, 4096]
- `llm.default_max_tokens_index`: 默认选中项索引（1，即 512）
- `llm.default_plugin_id`: 默认插件 ID（"llm-chat-default"）
