# 任务管理器插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：DataProvider 注册、实例化 `TaskService` + `MainWidget` |
| `function/services/core_service.py` | 任务 CRUD、统计计算、导出逻辑 |
| `ui/main_widget.py` | 任务列表、添加对话框、筛选、统计面板 |
| `config/default.json` | 默认插件 ID、优先级与状态列表配置 |

## 核心类
### `TaskService`
- `add_task(title, description, priority)`：生成 task_id，写入 DataProvider。
- `update_task_status(task_id, status)`：更新状态并发布 PUBLIC 事件。
- `get_tasks(status_filter)`：从 DataProvider 读取并可选筛选。
- `get_statistics()`：聚合各状态任务数量。
- `export_tasks(format)`：导出为 JSON/CSV。

## 关键设计决策
1. 任务数据存储在 `DataNamespace.PRIVATE`，统计信息存储在 `DataNamespace.PUBLIC`。
2. 每次状态变更触发 `_update_statistics()`，保持统计实时准确。
3. task_id 使用时间戳生成，保证唯一性。

## 配置
`config/default.json` 中：
- `defaults.plugin_id`: 默认插件 ID
- `defaults.priorities`: 支持的优先级列表
- `defaults.statuses`: 支持的状态列表
