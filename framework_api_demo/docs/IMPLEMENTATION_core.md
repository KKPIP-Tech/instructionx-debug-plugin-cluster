# Framework API Demo 插件 — 核心实现文档

- 修改日期：2026-07-30
- 对应版本：release.1.2.0

> 历史说明：旧版本的服务层曾集中于 `function/services/core_service.py` 单文件，
> 已在框架全 API 覆盖改造（2026-07-30，见 `docs/req/2026-07-30/`）中
> 拆分为 `function/services/` 包，core_service.py 已删除。

## 架构

| 文件 | 职责 |
|------|------|
| `entrance.py` | 插件胶水层：PluginServices 构造注入、生命周期（on_plugin_loaded / on_plugin_unloaded）、llm_tools 钩子、早期日志经 run_in_ui_thread 封送 |
| `information.py` | 插件元数据（IPluginInfo 实现）与 service_api 三方法声明 |
| `service.py` | FrameworkApiDemoService：service_api 实体实现（类名以 Service 结尾，构造签名兼容递减注入），内部委托 function/services 实现 |
| `function/services/base.py` | 服务基类 `Service`：统一解析框架依赖（PluginServices 注入优先、单例兜底）、配置加载、事件通知器 |
| `function/services/data_service.py` | DataDemoService：DataProvider 演示 |
| `function/services/task_service.py` | TaskDemoService：BackgroundTaskManager 演示 |
| `function/services/llm_service.py` | LLMDemoService：ILLMService（llm_facade）演示 |
| `function/services/api_service.py` | APIDemoService：PluginManager 演示 |
| `function/services/info_service.py` | FrameworkInfoService：框架信息与 utils 工具演示 |
| `function/services/mcp_service.py` | MCPDemoService：MCPManager / MCPClientManager 演示 |
| `function/tools/demo_tools.py` | 演示用 LLM 工具（get_current_time / calculate）的定义与 handler |
| `ui/main_widget.py` | 主控件布局壳：公共结果/日志面板 + Tab 容器 |
| `ui/tabs/` | 六个演示 Tab（base_tab 基座；llm_tab_groups.py 为 LLM 页多模态/统计分组 mixin） |
| `config/default.json` | 插件配置（task 间隔范围、demo 演示参数、mcp 远程演示配置） |

## 核心类

### `Service`（base.py）
服务基类。构造签名统一为 `(plugin_id, services=None, data_provider=None)`：
优先使用框架注入的 PluginServices 属性（data_provider / task_manager /
llm_facade / logger），缺失时回退对应框架单例，保证独立运行与测试场景可用。
提供 `set_event_notifier()` / `_notify_event()` 事件上抛通道。

### `DataDemoService`
封装 DataProvider 的注册/注销、私有/公共读写、资源存取、发布订阅与活跃实例查询。
demo_plugin_id 由 plugin_id 经确定性哈希生成（配置 `demo.plugin_id_prefix` /
`demo.plugin_id_hex_length`），订阅事件入有界缓存（上限 100 条）。

### `TaskDemoService`
封装 BackgroundTaskManager 的同步/异步/定时/长期任务、取消、状态查询与清理。
长期任务经闭包共享的 stop_event 优雅退出；定时任务间隔范围读取
`config/default.json` 的 `task` 段。

### `LLMDemoService`
全部经 `self.llm`（llm_facade）访问：Provider/模型查询、chat/stream_chat/embed、
会话管理、共享 ToolRegistry 注册与 chat_with_tools 多轮工具调用、
generate_image / text_to_speech（结果经 save_asset 落盘）、
get_usage_stats / validate_provider。
阻塞型调用（流式、会话发送、工具对话、多模态）一律经 register_sync_task
放入工作线程执行。

### `APIDemoService`
封装 PluginManager 的插件查询、API 发现、Function Tools 导出与跨插件调用。

### `FrameworkInfoService`
返回框架信息，并演示 LoggerManager 五级日志、thread_utils 线程封送、
FontMap 字体查询与 image_utils.load_image_as_base64。

### `MCPDemoService`
封装内置 MCP Server 生命周期（固定 streamable-http，避免 stdio 阻塞 UI）、
service_api 自动桥接工具清单（sanitize_tool_name(f"{plugin_id}__{method}")）
与远程 MCP Server 连接（同步契约，后台任务执行）。
mcp_manager / mcp_client 为 Optional 注入，未注入时返回统一错误字典。

## 事件协议（notifier 前缀机制）

工作线程回调产生的事件统一经基类 `_notify_event(str)` 上抛，UI 层注入
notifier 并自行 run_in_ui_thread 封送。LLM/MCP 演示用消息前缀区分事件类型，
各通道前缀独立避免串台：

- 流式聊天：`[流式片段] ` / `[流式完成]` / `[流式失败] `
- 会话：`[会话回复] ` / `[会话失败] ` / `[会话流式片段] ` / `[会话流式完成]` / `[会话流式失败] `
- 工具对话：`[工具对话完成]` / `[工具对话失败] `
- 多模态：`[图片生成完成]` / `[图片生成失败] ` / `[语音合成完成]` / `[语音合成失败] `

聚合结果（完整文本、usage 等）在工作线程写入服务实例的 `_last_*` 字段，
UI 收到完成事件后经 `get_last_*_result()` 拉取展示。

## 线程封送模式（notifier / run_in_ui_thread）

- 服务层不 import PySide6，事件只经 `_notify_event` 上抛字符串；
- UI 层（各 Tab）注入 notifier，回调中先 `run_in_ui_thread` 封送再更新控件；
- entrance 早期日志同样经 `run_in_ui_thread(self._deliver_log, message)` 投递
  （替代原 SignalBridge）。

## 卸载清理链（on_plugin_unloaded）

entrance 遍历已初始化的 data / task / llm 三个服务，逐个调用其 `cleanup()`
（异常仅记日志不逃逸）：

- `DataDemoService.cleanup()`：取消全部订阅（unsubscribe）、注销演示插件命名空间；
- `TaskDemoService.cleanup()`：停止全部长期任务、注销全部定时任务（逐项容错）；
- `LLMDemoService.cleanup()`：注销共享注册表中的演示工具、删除本插件创建的全部会话。

## 关键设计决策

1. 全部 LLM 调用走 ILLMService（llm_facade）契约，不直调 LLMProvider 单例。
2. 服务层按演示领域拆分为七个模块，`function/services/__init__.py` re-export
   全部服务类，外部引用保持稳定。
3. `service.py` 命名空间中只保留 FrameworkApiDemoService 一个类（委托服务经
   包模块间接引用），确保 PluginManager 按「类名以 Service 结尾」规则命中它。
4. 每个标签页独立封装，槽函数仅取输入、调服务、显示结果（≤5 行委托）。

## 配置

`config/default.json` 中：

- `task.default_interval`：默认定时间隔（60 秒）
- `task.interval_range`：间隔范围 [5, 3600]（UI SpinBox 实时读取）
- `demo.plugin_id_prefix` / `demo.plugin_id_hex_length`：demo_plugin_id 生成参数
- `demo.sync_task_seconds` / `demo.async_task_seconds`：演示任务耗时
- `mcp.remote_demo`：远程 MCP Server 演示配置（占位示例，需替换为实际启动命令）
