# Framework API Demo 插件

## 概述

Framework API Demo 插件用于演示 InstructionX 框架提供的核心 API 接口的使用方法，是一个帮助插件开发者了解框架能力的学习工具。

## 演示能力清单

以下均为插件代码中真实演示的能力：

### DataProvider（数据持久化）

- 注册 / 注销插件实例（`register_plugin()` / `unregister_plugin()`）
- 私有 / 公共命名空间数据读写（`get_plugin_data()` / `set_plugin_data()` / `get_all_plugin_data()`）
- 发布订阅通信（`subscribe()` / `publish()` / `unsubscribe()`，订阅事件经通知回调上抛 UI）
- 资源文件保存与加载（`save_asset()` / `load_asset()`）
- 活跃实例查询（`get_active_instance()`）

### BackgroundTaskManager（后台任务）

- 同步 / 异步任务创建（`register_sync_task()` / `register_async_task()`，带完成回调）
- 定时任务创建、启用 / 禁用、注销（`register_scheduled_task()` / `enable_scheduled_task()` / `disable_scheduled_task()` / `unregister_scheduled_task()`）
- 长期任务创建与优雅停止（`register_long_running_task()` / `stop_long_running_task()` / `update_long_running_task_status()`，stop_event 模式）
- 任务取消与状态查询（`cancel_task()` / `get_task_status()` / `get_task()`）
- 任务列表查询与已完成任务清理（`get_tasks_by_plugin()` / `get_scheduled_tasks()` / `get_long_running_tasks()` / `clear_completed_tasks()`）
- 定时任务间隔范围由 `config/default.json` 的 `task` 段配置（UI SpinBox 实时读取）

### ILLMService（llm_facade，LLM 插件服务门面）

- Provider 实例列表（`list_providers()` / `get_default_provider_id()` / `resolve_provider_id()`）
- 模型列表查询（`get_models()`）
- 聊天（`chat()`）与流式聊天（`stream_chat()`，后台任务执行 + 片段事件上抛 UI）
- 嵌入（`embed()`）
- 会话管理（`create_conversation()` / `send_message()` / `stream_send_message()` / `get_conversation()` / `list_conversations()` / `delete_conversation()`）
- 工具调用（共享 `ToolRegistry` 注册 / 注销 / 查询 + `chat_with_tools()` 多轮循环；入口经 `IPlugin.llm_tools` 声明工具清单）
- 多模态（`generate_image()` / `text_to_speech()`，结果经 `save_asset()` 落盘）
- 用量统计与 Provider 校验（`get_usage_stats()` / `validate_provider()`）

### PluginManager（插件管理）

- 插件查询（`get_all_plugins()` / `get_plugin_by_id()`）
- API 发现（`get_all_apis()` / `get_api_description()`）
- Function Tools 导出（`get_all_function_tools()`）
- 跨插件调用（`call_plugin_method()`）

### MCPManager / MCPClientManager（MCP 协议）

- 内置 MCP Server 状态查询与启停（`get_server_config()` / `is_server_running()` / `get_server_url()` / `start_server()` / `stop_server()`）
- service_api 自动桥接工具清单（工具名 `{plugin_id}__{method}` 净化版）
- 远程 MCP Server 连接 / 断开 / 列表 / 工具查询（`connect()` / `disconnect()` / `list_connected_servers()` / `list_tools()`，同步契约，后台任务执行）

### 框架工具（utils / 主题）

- `LoggerManager` 五级日志（`debug()` / `info()` / `warning()` / `error()` / `critical()`）
- 线程封送（`is_ui_thread()` / `run_in_ui_thread()` / `run_in_ui_thread_sync()`）
- FontMap 字体查询（`FontMap.all_fonts()` / `FontMap.get()`）
- 图片转 Base64（`image_utils.load_image_as_base64()`）
- 主题跟随（`ThemeManager.theme_changed` 信号监听）

## 跨插件 API（service_api）

插件通过 `information.py` 的 `service_api` 声明 + `service.py` 的 `FrameworkApiDemoService` 实体，
经框架自动注册机制暴露以下跨插件 API（同时同步为 MCP 工具）：

| 方法 | 功能 | 参数 |
|------|------|------|
| `demo_data_operation` | 演示 DataProvider 数据操作 | `operation`（read/write/list，必填）、`key`、`value` |
| `demo_task_operation` | 演示任务操作 | `operation`（create/query/cancel，必填）、`task_type`（sync/async/scheduled）、`task_id`（cancel 必填） |
| `get_framework_info` | 获取框架信息 | 无 |

## 使用说明

### 启动插件

1. 运行 InstructionX 主程序
2. 在插件列表中找到 "Framework API Demo" 插件
3. 点击切换到该插件

### 功能标签页

1. **DataProvider** - 数据存取、发布订阅、资源管理、活跃实例查询
2. **Task** - 同步/异步/定时/长期任务，取消、启停与状态查询
3. **LLM** - Provider/模型查询、聊天、流式聊天、嵌入、会话管理、工具调用、多模态、用量统计与校验
4. **API** - 插件查询、API 发现、Function Calling、跨插件调用
5. **Info** - 框架信息、日志级别、线程封送、字体与资源、主题跟随、接口文档
6. **MCP** - 内置 MCP Server 启停、service_api 桥接工具、远程 Server 连接

### 注意事项

1. **LLM 功能**: 需要先在主程序中配置 LLM Provider 才能使用聊天、嵌入、会话、工具调用与多模态功能
2. **定时任务**: 定时任务会在后台自动执行，不需要保持插件界面打开
3. **MCP 功能**: 依赖框架注入的 mcp_manager / mcp_client（框架未启用 MCP 时页面会提示不可用）；远程演示服务器配置为占位示例，需替换为实际 MCP Server 启动命令
4. **资源管理**: 保存的资源文件存储在 `data/assets/plugins/` 目录下
5. **日志**: 所有操作都会记录在底部的日志区域

## 文件结构

```
framework_api_demo/
├── __init__.py             # 包初始化
├── entrance.py             # 插件入口（胶水层：PluginServices 注入、生命周期、llm_tools、主控件创建）
├── information.py          # 插件元数据与 service_api 声明
├── service.py              # FrameworkApiDemoService：service_api 实体实现（跨插件 API / MCP 工具）
├── IXPlugin.json           # GitHub 安装描述文件
├── config/
│   └── default.json        # 插件配置（task 间隔范围、demo 演示参数、mcp 远程演示配置）
├── function/
│   ├── services/           # 服务层（业务逻辑）
│   │   ├── base.py         #   服务基类（依赖解析 + 配置加载 + 事件通知）
│   │   ├── data_service.py #   DataProvider 演示
│   │   ├── task_service.py #   BackgroundTaskManager 演示
│   │   ├── llm_service.py  #   ILLMService（llm_facade）演示
│   │   ├── api_service.py  #   PluginManager 演示
│   │   ├── info_service.py #   框架信息与 utils 工具演示
│   │   └── mcp_service.py  #   MCPManager / MCPClientManager 演示
│   └── tools/
│       └── demo_tools.py   #   演示用 LLM 工具定义与 handler（get_current_time / calculate）
├── ui/
│   ├── main_widget.py      # 主控件（布局壳：公共结果/日志面板 + Tab 容器）
│   └── tabs/               # 各功能标签页（base/data/task/llm/api/info/mcp；
│                           #   llm_tab_groups.py 为 LLM 页多模态/统计分组 mixin）
└── docs/                   # 设计与需求文档
```

## 依赖

本插件不依赖额外的第三方库，仅使用 InstructionX 框架提供的内置模块。

## 版本

- **版本**: release.1.0.2
- **开发者**: InstructionX
- **许可**: 免费
