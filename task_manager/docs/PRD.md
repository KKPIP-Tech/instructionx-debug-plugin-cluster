# 任务管理器插件 — 产品需求文档

## 概述
提供任务创建、状态跟踪、筛选和统计功能，支持数据持久化。

## 功能需求
- **任务 CRUD**：创建、读取、更新状态、删除任务。
- **优先级**：支持 low / normal / high 三级优先级。
- **状态流转**：pending → in_progress → completed / cancelled。
- **筛选**：按状态筛选任务列表。
- **统计**：实时显示任务总数、各状态数量。
- **导出**：将任务数据导出为 JSON 或 CSV。

## 非功能需求
- 数据通过 `DataProvider` 持久化。
- 发布公共事件（task_added, status_changed 等），供其他插件订阅。

## 依赖
- `core.plugin.plugin_interface.IPlugin`
- `core.data.data_provider.DataProvider`
- `PySide6.QtWidgets`
