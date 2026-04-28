# LLM Chat 插件 — 产品需求文档

## 概述
提供功能完整的 LLM 对话界面，支持流式输出、多模态图片、参数调节和对话历史管理。

## 功能需求
- **Provider/Model 选择**：下拉框选择 LLM Provider 和具体模型。
- **流式输出**：实时逐字显示 AI 回复，支持中途停止。
- **参数调节**：Temperature（0.0–1.0）、Max Tokens 调节。
- **多模态**：支持添加图片进行 Vision 对话。
- **对话历史**：保存多轮对话，支持点击查看详情和清除。
- **全局同步**：响应主窗口的 LLM Provider 切换事件。

## 非功能需求
- 聊天请求在独立线程（QThread）中执行，不阻塞 UI。
- 网络错误分类处理：认证失败、频率限制、超时、连接失败。
- 偏好设置（Provider、Model）持久化到 DataProvider。

## 依赖
- `core.plugin.plugin_interface.IPlugin`
- `core.data.data_provider.DataProvider`
- `core.llm.llm_provider`
- `PySide6.QtWidgets`
