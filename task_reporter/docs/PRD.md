# 任务报告生成器插件 — 产品需求文档

## 概述
订阅任务管理器的数据变更，生成统计报告并支持多格式导出。

## 功能需求
- **自动订阅**：自动发现并订阅活跃的 TaskManager 实例。
- **统计报告**：实时显示任务完成率、待办比例等性能指标。
- **多格式导出**：支持 JSON、TXT、HTML 三种报告格式。
- **事件历史**：记录并展示 TaskManager 的事件日志。
- **自动刷新**：每 3 秒自动刷新统计数据和事件列表。

## 非功能需求
- 订阅失败时给出明确提示。
- 报告生成过程不阻塞 UI。

## 依赖
- `core.plugin.plugin_interface.IPlugin`
- `core.data.data_provider.DataProvider`
- `PySide6.QtWidgets`
