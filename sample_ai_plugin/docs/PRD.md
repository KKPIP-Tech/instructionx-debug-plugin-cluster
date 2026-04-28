# 示例 AI 插件 — 产品需求文档

## 概述
展示如何在 InstructionX 框架中集成 LLM 能力，支持同步聊天、流式输出和 Function Calling。

## 功能需求
- **同步聊天**：发送单轮消息，获取完整回复。
- **流式输出**：实时逐字显示 AI 回复。
- **Function Calling**：演示工具注册与自动调用。
- **Provider 切换**：支持在不同 LLM Provider 间切换。

## 非功能需求
- 流式输出不阻塞 UI。
- 网络错误时给出明确提示。

## 依赖
- `core.plugin.plugin_interface.IPlugin`
- `core.llm.llm_provider`
- `PySide6.QtWidgets`
