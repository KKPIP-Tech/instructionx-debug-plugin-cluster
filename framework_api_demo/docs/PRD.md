# Framework API Demo 插件 — 产品需求文档

> **取代说明（2026-07-30）**：本 PRD 为 release.1.0.x~1.1.0 时期的初版需求，
> 已被 2026-07-30 的「框架全 API 覆盖改造」需求文档取代并扩展，当前有效 PRD 为
> `docs/req/2026-07-30/PRD-full-api-coverage-20260730.md`
> （配套 SPEC：`SPEC-full-api-coverage-20260730.md`）。
> 本文件保留作历史参考，下列内容不再代表现状（现状以 README 与新 PRD/SPEC 为准）。

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
