# 任务报告生成器插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：DataProvider 注册、实例化 `ReporterService` + `MainWidget` |
| `function/services/core_service.py` | 订阅管理、报告生成、事件日志持久化 |
| `ui/main_widget.py` | 订阅面板、统计展示、报告生成、事件历史 |
| `config/default.json` | 自动刷新间隔与事件历史限制配置 |

## 核心类
### `ReporterService`
- `get_active_task_manager_id()`：通过 DataProvider 获取活跃的 TaskManager ID。
- `subscribe_to_task_manager(manager_id)`：订阅统计信息和事件变更。
- `get_statistics_report(manager_id)`：计算完成率、比例等性能指标。
- `generate_report(manager_id, format)`：生成 JSON/TXT/HTML 报告并保存为资源。
- `get_event_history(limit)`：读取本地缓存的事件日志。

## 关键设计决策
1. 使用 DataProvider 的 `subscribe`/`unsubscribe` 机制实现实时数据同步。
2. 事件日志同时保存在内存和 DataProvider 中，支持跨会话恢复。
3. 自动刷新使用 `QTimer`，间隔可配置。

## 配置
`config/default.json` 中：
- `refresh.interval_ms`: 自动刷新间隔（3000ms）
- `refresh.event_history_limit`: 事件历史显示数量限制（20）
