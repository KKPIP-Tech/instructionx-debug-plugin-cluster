# PRD — framework_api_demo 框架全 API 覆盖改造

- 创建日期：2026-07-30
- 修改日期：2026-07-30
- 插件：framework-api-demo（官方示例插件，当前 release.1.1.0）
- 文档类型：产品需求文档（PRD）
- 配套文档：`SPEC-full-api-coverage-20260730.md`

---

## 1. 概述

### 1.1 背景与问题

framework_api_demo 的定位是「框架面向插件开放 API 的完整学习示例」。经审查，当前实现存在三类问题：

1. **API 覆盖不全**：仅覆盖了框架开放 API 的一个子集。缺失：DataProvider 发布订阅、长期任务/定时任务管理、stream_chat 流式聊天、会话管理、工具调用（ToolRegistry / chat_with_tools / IPlugin.llm_tools）、MCP 管理器与客户端、多模态（generate_image / text_to_speech）、用量统计与 Provider 校验、线程封送工具、FontMap、主题跟随、LoggerManager 分级日志、image_utils 等。
2. **方向性偏差**：
   - LLM 演示直接调用 `LLMProvider` 单例，绕过了框架为插件提供的 `ILLMService` 插件门面（`services.llm_facade`），与框架推荐的插件集成路径相悖；
   - `entrance.py` 未接收 `services: PluginServices` 构造注入（框架主路径），缺少 `on_plugin_unloaded` 卸载清理；
   - `information.py` 声明的 `service_api` 三方法（demo_data_operation / demo_task_operation / get_framework_info）在 `service.py` 中无真实实现（空壳），导致跨插件 API 与 MCP 自动桥接机制形同虚设。
3. **文档与代码不一致**：
   - README 声称演示 subscribe / 长期任务 / cancel_task / stream_chat，代码中并不存在；
   - README 文件结构描述过时、版本号错误；
   - `config/default.json` 中 `ui`、`plugin` 段未被任何代码消费，`version` 与实际版本不符，`task.interval_range` 未被读取（UI 硬编码 5/3600/60）。

### 1.2 改造目标

将 framework_api_demo 改造为**覆盖框架面向插件开放的全部 API 的使用方法**的学习基准插件：

- 每一个框架开放 API 都有对应的真实、可运行、有 UI 反馈的演示；
- 所有演示均走框架推荐的插件集成路径（PluginServices 注入、ILLMService 门面）；
- service_api 空壳修复为真实实现，使跨插件 API 与 MCP 自动桥接机制可被实际验证；
- 文档（README）与代码行为完全一致。

### 1.3 核心价值

- 插件开发者可通过阅读与运行本插件，一站式学习框架全部开放 API 的正确用法；
- 作为框架 API 变更的回归参照：框架接口演进时，本插件可充当活文档与手工验证基准；
- 纠偏后的实现本身就是「插件开发最佳实践」的可执行示例。

### 1.4 非目标

- 不新增框架侧功能、不修改框架代码；
- 不改变插件 id（`framework-api-demo`）、不改变 service_api 三方法的对外签名；
- 不做打包/发布流程，不涉及其他示例插件。

---

## 2. 用户故事（插件开发者视角）

- **US-1**：作为插件开发者，我希望在示例插件中看到 `PluginServices` 构造注入的标准写法，以及通过它获取 data_provider / task_manager / llm_facade / logger / mcp_manager / mcp_client 的范例，以便照搬到自己的插件。
- **US-2**：作为插件开发者，我希望看到 `on_plugin_unloaded` 中完整的清理范例（取消订阅、注销演示插件、停止定时任务），以便理解插件热卸载时应做什么。
- **US-3**：作为插件开发者，我希望所有 LLM 调用都通过 `services.llm_facade`（ILLMService 契约）完成，而不是直接摸框架内部单例，以便写出不受框架内部重构影响的插件。
- **US-4**：作为插件开发者，我希望看到 DataProvider 发布订阅的完整闭环（subscribe / publish / unsubscribe），并理解回调在工作线程执行、必须经 `run_in_ui_thread` 封送更新 UI。
- **US-5**：作为插件开发者，我希望看到后台任务的完整能力演示：普通任务、带 stop_callback/status_callback 的长期任务、停止/取消、完成回调、定时任务的启停与注销。
- **US-6**：作为插件开发者，我希望看到流式聊天 `stream_chat` 的 `callback(str, done)` 契约如何逐步刷新 UI。
- **US-7**：作为插件开发者，我希望插件声明的 service_api 有真实实现，并能通过跨插件调用与 MCP 工具两种方式实际触发，以便理解自动桥接机制。
- **US-8**：作为插件开发者，我希望看到会话管理全流程（创建、发消息、流式发消息、查询、列表、删除）的演示。
- **US-9**：作为插件开发者，我希望看到如何注册工具到共享 ToolRegistry、如何用 `chat_with_tools` 跑多轮工具调用、以及入口插件如何通过 `IPlugin.llm_tools` 声明工具。
- **US-10**：作为插件开发者，我希望看到 MCP Server 生命周期管理与 MCP Client 连接外部 Server 的同步调用方法演示。
- **US-11**：作为插件开发者，我希望看到多模态（图像生成、语音合成）、用量统计、Provider 列表与校验的演示。
- **US-12**：作为插件开发者，我希望看到线程封送、FontMap 字体、ThemeManager 主题跟随、LoggerManager 五级日志、图片转 base64 等工具类 API 的演示。
- **US-13**：作为插件开发者，我希望 README、配置文件与代码行为完全一致，不存在「声称演示但未实现」的条目。

---

## 3. 功能需求

> 分两批实施；每批内按功能颗粒度单独 commit（详见 SPEC 实施计划）。

### 第一批（纠偏 + 补核心）

- **FR-1 UI 重构（tabs 包拆分）**
  - 将 `ui/main_widget.py`（871 行）拆分为 `ui/tabs/` 包：`base_tab`、`data_tab`、`task_tab`、`llm_tab`、`api_tab`、`info_tab`，并为后续 `mcp_tab` 预留结构；
  - `main_widget.py` 只保留布局壳（QTabWidget 装配）与公共结果/日志面板；
  - 演示 API：InstructionX_UIKit 组件与 `T()` 令牌（纯 UI 层，无业务逻辑）。

- **FR-2 PluginServices 构造注入与服务层拆分**
  - `entrance.py` 构造函数接收 `services: PluginServices` 并透传；服务层统一经 PluginServices 获取 `data_provider` / `task_manager` / `llm_facade` / `logger` / `mcp_manager` / `mcp_client`；
  - 实现 `on_plugin_unloaded`：取消全部 DataProvider 订阅、注销演示插件命名空间、停止并注销定时任务；
  - `function/services/core_service.py`（442 行）拆分为 `function/services/` 包：`base.py`（公共基类：结果字典、日志辅助、配置读取）、`data_service.py`、`task_service.py`、`llm_service.py`、`api_service.py`、`info_service.py`、`mcp_service.py`，`__init__.py` re-export 保持外部引用稳定；
  - 演示 API：PluginServices 六属性、IPlugin.on_plugin_loaded / on_plugin_unloaded、框架注入的 `_plugin_id` / `_plugin_dir`。

- **FR-3 LLM 演示改走 llm_facade（ILLMService 门面）**
  - 移除对 `LLMProvider` 单例的直接调用，全部改为 `services.llm_facade`；
  - 演示 API：`chat`、`embed`、`get_models(provider="default")`、`last_stream_response` 属性。

- **FR-4 DataProvider 发布订阅演示**
  - 演示 API：`subscribe(subscriber_id, target_plugin_id, target_key, callback)`、`publish(publisher_id, key, value, namespace=PUBLIC)`、`unsubscribe`；
  - 明确展示：订阅回调在工作线程执行，UI 更新必须经 `run_in_ui_thread` 封送；
  - 配合既有 `register/unregister_plugin`、`get/set_active_instance`、`get/set_plugin_data`（PRIVATE/PUBLIC）演示形成完整数据页。

- **FR-5 任务演示补全**
  - 演示 API：`register_long_running_task(func, callback, stop_callback, status_callback, auto_restart)`、`stop_long_running_task`、`get_long_running_tasks`、`cancel_task`、普通任务完成 `callback`、`register_scheduled_task(interval, callback)`、`enable_scheduled_task` / `disable_scheduled_task` / `unregister_scheduled_task`、`get_task` / `get_tasks_by_plugin` / `get_task_status` / `get_scheduled_tasks` / `clear_completed_tasks`；
  - 定时任务 interval 上下限从 `config/default.json` 的 `task.interval_range` 读取（替代 UI 硬编码 5/3600/60）。

- **FR-6 stream_chat 流式聊天演示**
  - 演示 API：`llm_facade.stream_chat(prompt, callback)`，遵循 `callback(chunk: str, done: bool)` 契约，逐步刷新显示；配合 `last_stream_response` 展示完整响应。

- **FR-7 修复 service_api 空壳与配置/README 一致性**
  - `service.py` 提供以 `Service` 结尾的实体类，真实实现 `demo_data_operation` / `demo_task_operation` / `get_framework_info`；构造签名兼容 `(plugin_id, data_provider, llm_service, task_manager)` 递减注入；
  - `config/default.json`：移除未被消费的 `ui` / `plugin` 段（或改为真实消费，二选一并在 SPEC 中定案），`version` 与实际一致，`task.interval_range` 由代码真实读取；
  - README 修复：文件结构、版本号、删除「声称演示但未实现」条目，改为如实描述。

### 第二批（补全）

- **FR-8 会话管理演示**
  - 演示 API：`create_conversation(system_prompt=None, provider, model, metadata=None) -> str`、`send_message(conv_id, content, images=None, ...)`、`stream_send_message(conv_id, content, images, callback(StreamChunk), ...)`、`get_conversation`、`list_conversations`、`delete_conversation`。

- **FR-9 工具调用演示**
  - 演示 API：`get_shared_tool_registry().register()` 注册演示工具、`chat_with_tools(...) -> ToolChatResult`、入口插件实现 `IPlugin.llm_tools` 属性（声明 function-calling 工具字典列表）；
  - 可选展示 `get_tool_executor` / `chat_with_tools_stream`。

- **FR-10 MCP 演示页（mcp_tab）**
  - 演示 API（mcp_manager）：`start_server` / `stop_server` / `is_server_running` / `get_server_url` / `get_server_config`（可选 `update_server_config`）；
  - 演示 API（mcp_client，MCPClientManager，同步方法勿 await）：`connect` / `disconnect` / `list_connected_servers` / `list_tools`；
  - 页面内以说明文案 + 实机验证方式解释 `service_api` → 跨插件 API → MCP 工具（工具名 `{plugin_id}__{method}` 净化版）的自动桥接机制。

- **FR-11 多模态与统计演示**
  - 演示 API：`generate_image(prompt, provider, model=None, size, quality) -> ImageResult`、`text_to_speech(text, provider, model=None, voice=None) -> AudioResult`、`get_usage_stats(conversation_id=None)`、`validate_provider(provider) -> Tuple[bool, str]`、`list_providers() -> List[ProviderInfo]`、`get_default_provider_id(feature="chat")`、`resolve_provider_id`。

- **FR-12 工具与主题演示**
  - 演示 API：`run_in_ui_thread` / `run_in_ui_thread_sync` / `is_ui_thread`、`FontMap.get(family, variant, weight) -> FontInfo` 与 `all_fonts()`（枚举 FontFamily / FontVariant / FontWeight）、`ThemeManager.instance().theme_changed` 主题跟随（Signal(str) connect）、`LoggerManager` 五个级别（debug/info/warning/error/critical，演示自行 `traceback.format_exc()` 拼接异常堆栈）、`image_utils.load_image_as_base64`。

---

## 4. 非功能需求

- **NFR-1 性能**：所有演示操作不得阻塞 UI 线程。LLM 调用、任务类演示一律走 BackgroundTaskManager 或流式回调；工作线程回调更新 UI 必须经 `run_in_ui_thread` 封送；长时间运行的演示提供停止手段。
- **NFR-2 安全**：插件不包含、不要求任何硬编码密钥；LLM/MCP 演示使用用户在应用设置中已配置的 Provider 与 MCP Server；不在日志与结果面板输出敏感配置（如 API Key、Bearer Token）。
- **NFR-3 兼容性**：
  - `service_api` 三方法（`demo_data_operation` / `demo_task_operation` / `get_framework_info`）的**对外签名保持向后兼容**，仅填充实现，不改变参数与返回结构（返回 `{"success": bool, ...}` 字典模式）；
  - 保持 `demo_plugin_id` 的确定性哈希机制不变（DataProvider 演示命名空间不得因改造而改变生成规则）；
  - 插件 id `framework-api-demo` 不变，已安装用户的插件 UUID 与数据不受影响。
- **NFR-4 代码规范**（硬约束，验收标准）：
  - 分层：entrance.py 胶水层；service.py 对外接口层（Service 结尾类）；function/ 业务逻辑（禁 QWidget/PySide6）；ui/ 只做视图与事件分发（槽函数 ≤5 行委托服务层）；
  - 函数/方法 ≤20 行；嵌套 ≤3 层；无魔法数（字面量入 `config/default.json` 或命名常量）；import 全部置顶分组；禁止裸 except 与静默吞异常；注释/docstring 中文；type hints 完整；
  - UI 样式只用 InstructionX_UIKit 组件 + `T()` 令牌；
  - 单文件一个内聚主题，臃肿即拆包 + `__init__.py` re-export。
- **NFR-5 文档一致性（修复既有不一致）**：
  - service_api 三方法必须有实体实现（修复「声明无实体」）；
  - README 声称演示 subscribe / 长期任务 / cancel_task / stream_chat 的条目必须与代码一致（实现后如实保留，未实现不得声称）；
  - `config/default.json` 的 `task` / `ui` / `plugin` 段必须被代码真实消费或移除，禁止「死配置」；
  - 每次 commit 后 README 文件结构小节保持最新。

---

## 5. 插件类型判断

- 本插件为**单插件集内的既有官方示例插件**（`plugin/` 仓库一级子目录，kebab-case 目录 `framework-api-demo`）；
- 插件 id **保持 `framework-api-demo` 不变**；本次为原地改造，不涉及新插件创建、拆分或迁移；
- 分类归属不变：KKPIP-Tech 组织下的官方插件。

---

## 6. 描述文件清单

- **`IXPlugin.json`**：内容（id、名称、入口声明等）无需结构性改动；仅 `version` 字段随发版更新。
- **版本号建议**：本次为功能大幅扩展（API 覆盖面成倍增加 + 服务层/UI 结构性重构），按语义化建议由 `release.1.1.0` 升至 **`release.1.2.0`**（次版本号 +1，新增能力且向后兼容）。**最终版本号由开发者确认**，未经确认不得擅自修改。
- 其他描述/配置文件：
  - `information.py`：service_api 声明保持不变（描述文案可随实现细化），版本随发版更新；
  - `config/default.json`：按 FR-7 清理/真实消费；
  - `README.md`：按 FR-7 / NFR-5 全面修订。

---

## 7. 验收标准（摘要）

1. 上述 FR-1 ~ FR-12 列出的每个 API 在插件 UI 中均可实际操作并看到结果/错误反馈；
2. 全代码库 grep 不到对 `LLMProvider` 单例的直接使用（llm_facade 除外路径不存在）；
3. 插件热卸载后无残留订阅、无残留定时任务、无残留演示插件命名空间；
4. README、`config/default.json`、代码三者一致；
5. 满足 NFR-4 全部硬性规范；方法行数、嵌套层级抽查通过。
