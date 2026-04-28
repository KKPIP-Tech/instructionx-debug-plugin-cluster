# 后台任务演示器插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 插件生命周期、SignalBridge、定时任务工厂注册 |
| `function/services/core_service.py` | 后台任务管理 API（查询、创建、取消） |
| `ui/main_widget.py` | 任务创建面板、任务列表、执行日志 |
| `config/default.json` | 默认任务时长与间隔范围配置 |

## 核心类
### `SignalBridge` (QObject)
- `task_completed` Signal：线程安全地将任务完成信息传递到主线程。
- `task_updated` Signal：触发任务列表刷新。

### `MainWidget`
- `_create_task()`：根据用户选择创建 sync/async/scheduled 任务。
- `_cancel_task()`、`_clear_completed()`：任务生命周期管理。
- `_log()`：支持 UI 就绪前写入缓冲区的日志系统。

## 关键设计决策
1. `SignalBridge` 在 `__init__` 中创建，确保 UI 创建前就能接收回调。
2. 全局 `_log_buffer` 解决 UI 未就绪时的日志记录问题。
3. 定时任务工厂在 `on_plugin_loaded` 中注册，支持无 UI 场景。

## 配置
`config/default.json` 中：
- `task.default_duration`: 默认执行时长（2 秒）
- `task.duration_range`: 时长范围 [1, 30]
- `task.default_interval`: 默认定时间隔（10 秒）
- `task.interval_range`: 间隔范围 [5, 3600]
