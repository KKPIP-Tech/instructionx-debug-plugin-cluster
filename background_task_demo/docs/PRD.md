# 后台任务演示器插件 — 产品需求文档

## 概述
演示 InstructionX 框架 BackgroundTask 模块的全部功能，包括同步/异步/定时任务。

## 功能需求
- **同步任务**：注册并立即执行的阻塞任务。
- **异步任务**：注册后在后台线程执行的任务。
- **定时任务**：按固定间隔重复执行的任务。
- **任务管理**：取消任务、清理已完成任务、查看任务状态。
- **恢复机制**：插件重启后恢复定时任务工厂。

## 非功能需求
- 任务回调通过 SignalBridge 安全更新 UI。
- 日志支持 UI 未创建时的缓冲区模式。

## 依赖
- `core.plugin.plugin_interface.IPlugin`
- `core.task.BackgroundTaskManager`
- `PySide6.QtWidgets`
