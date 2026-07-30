# Framework API Demo 插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 插件胶水层、生命周期、日志系统（run_in_ui_thread 封送） |
| `function/services/core_service.py` | 5 个 Service 类：DataDemoService、TaskDemoService、LLMDemoService、APIDemoService、FrameworkInfoService |
| `information.py` | 插件元数据（IPluginInfo 实现） |
| `config/default.json` | 任务默认间隔配置 |

## 核心类
### `DataDemoService`
封装 DataProvider 的 register/write/read/save_asset/load_asset 操作。

### `TaskDemoService`
封装 BackgroundTaskManager 的 sync/async/scheduled 任务创建与查询。

### `LLMDemoService`
封装 LLMProvider 的 get_providers、get_models、chat、embed 接口。

### `APIDemoService`
封装 PluginManager 的 get_all_plugins、get_all_apis、get_all_function_tools、call_plugin_method。

### `FrameworkInfoService`
返回框架静态信息。

## 关键设计决策
1. 5 个 Service 类分别对应 5 个框架模块，职责清晰。
2. 早期日志经 `run_in_ui_thread` 封送到 UI 线程更新日志面板（替代原 SignalBridge）。
3. 每个标签页独立封装，互不干扰。

## 配置
`config/default.json` 中：
- `task.default_interval`: 默认定时间隔（60 秒）
- `task.interval_range`: 间隔范围 [5, 3600]
