# API Demo 插件 — 产品需求文档

## 概述
演示 InstructionX 框架的跨插件 API 调用机制，展示如何发现和使用其他插件暴露的 API。

## 功能需求
- **API 发现**：列出当前系统中所有插件暴露的 API 方法。
- **API 调用**：输入参数，调用目标插件的方法并展示结果。
- **方法说明**：显示每个 API 方法的参数和返回值说明。

## 非功能需求
- 调用失败时捕获异常并展示友好错误信息。
- 支持文本类型的输入和输出。

## 依赖
- `core.plugin.plugin_interface.IPlugin`
- `core.plugin.manager.PluginManager`
- `PySide6.QtWidgets`
