# Framework API Demo 插件 — 产品需求文档

## 概述
全面演示 InstructionX 框架提供的所有核心 API 接口，是开发者学习框架的最佳示例。

## 功能需求
- **DataProvider 演示**：插件注册/注销、私有/公共数据读写、资源管理。
- **BackgroundTask 演示**：同步、异步、定时任务的创建与查询。
- **LLM 演示**：Provider 列表、模型列表、聊天、嵌入测试。
- **PluginManager 演示**：插件查询、API 发现、Function Tools、跨插件调用。
- **框架信息**：显示框架版本与可用接口文档。

## 非功能需求
- 每个操作都有执行日志记录。
- 错误操作捕获异常并展示友好提示。

## 依赖
- `core.plugin.plugin_interface.IPlugin`
- `core.data.data_provider.DataProvider`
- `core.task.BackgroundTaskManager`
- `core.llm.llm_provider.LLMProvider`
- `core.plugin.manager.PluginManager`
- `PySide6.QtWidgets`
