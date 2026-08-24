# InstructionX Official Plugins

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-6.10+-green.svg)](https://doc.qt.io/qtforpython/)

**InstructionX 框架官方插件集合（Debug Plugin Cluster）**

</div>

---

## 项目简介

本仓库包含 **InstructionX 框架**的官方插件集合：Framework API Demo（框架核心 API 演示）、UI Demo（InstructionX_UIKit 组件体系展示）与 Blueprint OpenCV（蓝图节点化 OpenCV 图像处理）。三个插件版本与仓库 Git Tag 统一。

### 主要特性

- **插件热插拔**：无需重启应用即可加载/卸载插件
- **框架 API 访问**：直接调用 DataProvider、BackgroundTaskManager、LLMProvider 等核心服务
- **MCP 协议支持**：插件可作为 MCP tools 暴露 API 供外部 LLM 调用
- **多语言支持（i18n）**：三个插件均提供 `text/zh.xml` 与 `text/en.xml` 语言包，跟随框架语言实时切换，亦可在插件管理对话框中按插件单独设置语言
- **跨插件通信**：通过 PluginManager 实现插件间方法调用
- **PySide6 UI**：基于 Qt 的现代化用户界面

---

## 插件列表

| 插件 | ID | 描述 |
|------|-----|------|
| **Framework API Demo** | `framework-api-demo` | 框架所有核心 API 的完整演示，包括 DataProvider、BackgroundTaskManager、LLMProvider、PluginManager、LoggerManager、FontManager |
| **UI Demo** | `ui-demo` | InstructionX_UIKit 组件体系展示，包括基础控件、输入、展示、反馈、布局、动画、图表、蓝图节点图等 |
| **Blueprint OpenCV** | `blueprint-opencv` | 蓝图节点化 OpenCV 图像处理：拖拉拽节点、参数调节、实时预览、蓝图工作流存档管理 |

---

## 框架 API 参考

### 1. DataProvider (core/data/data_provider.py)

| 接口 | 功能 | 正常状态 | 错误状态 |
|-----|------|---------|---------|
| `register_plugin()` | 注册插件实例 | 返回 None | `DataProviderError`: 插件已存在 |
| `unregister_plugin()` | 注销插件实例 | 返回 None | `DataProviderError`: 插件不存在 |
| `set_active_instance()` | 设置活跃实例 | 返回 None | `DataProviderError`: 插件不存在 |
| `get_active_instance()` | 获取活跃实例 | 返回 instance_id 或 None | - |
| `get_plugin_data()` | 读取插件数据 | 返回数据值或默认值 | `DataProviderError`: 插件不存在 |
| `set_plugin_data()` | 写入插件数据 | 返回 None | `DataProviderError`: 插件不存在 |
| `subscribe()` | 订阅数据变化 | 返回 None | `DataProviderError`: 目标插件不存在 |
| `save_asset()` | 保存资源文件 | 返回相对路径 | `DataProviderError`: 保存失败 |
| `load_asset()` | 加载资源文件 | 返回 bytes | `DataProviderError`: 加载失败 |

### 2. BackgroundTaskManager (core/task/background_task.py)

| 接口 | 功能 | 正常状态 | 错误状态 |
|-----|------|---------|---------|
| `register_sync_task()` | 注册同步任务（在调用线程**立即执行**） | 返回 task_id | - |
| `register_async_task()` | 注册异步任务（在线程池后台执行） | 返回 task_id | - |
| `register_scheduled_task()` | 注册定时任务 | 返回 task_id | - |
| `register_long_running_task()` | 注册长期任务 | 返回 task_id | - |
| `stop_long_running_task()` | 停止长期任务（可清理存储残留） | 返回 True/False | - |
| `is_long_task_running()` | 判定长期任务是否运行中 | 返回 True/False | - |
| `get_tasks_by_plugin()` | 获取插件任务列表 | 返回 List[BackgroundTask] | - |
| `get_scheduled_tasks()` | 获取定时任务列表 | 返回 List[ScheduledTask] | - |
| `get_task_status()` | 获取任务状态 | 返回 TaskStatus 或 None | - |
| `cancel_task()` | 取消任务 | 返回 True/False | - |
| `clear_completed_tasks()` | 清理已完成任务 | 返回清理数量 | - |

### 3. LLMProvider (core/llm/llm_provider.py)

| 接口 | 功能 | 正常状态 | 错误状态 |
|-----|------|---------|---------|
| `chat()` | 发送聊天请求 | 返回 ChatResponse | `ConfigurationError`: 无可用 Provider |
| `stream_chat()` | 流式聊天 | 返回生成器 | `ConfigurationError`: Provider 不存在 |
| `async_chat()` | 异步聊天 | 返回 ChatResponse | `ConfigurationError`: 无可用 Provider |
| `embed()` | 发送嵌入请求 | 返回 EmbeddingResponse[] | `ConfigurationError`: 无可用 Provider |
| `get_all_providers()` | 获取所有 Provider | 返回 Dict[str, ILLM] | - |
| `get_enabled_providers()` | 获取已启用 Provider | 返回 Dict[str, ILLM] | - |
| `get_cached_models()` | 获取缓存模型列表 | 返回 List[ModelInfo] | - |
| `get_models()` | 获取模型列表 | 返回 Dict[str, List[ModelInfo]] | - |
| `get_provider()` | 获取指定 Provider | 返回 ILLM 或 None | - |

### 4. PluginManager (core/plugin/manager.py)

| 接口 | 功能 | 正常状态 | 错误状态 |
|-----|------|---------|---------|
| `get_all_plugins()` | 获取所有插件 | 返回 List[IPlugin] | - |
| `get_plugin_by_id()` | 通过 ID 获取插件 | 返回 IPlugin 或 None | - |
| `get_plugin_by_name()` | 通过名称获取插件 | 返回 IPlugin 或 None | - |
| `register_plugin_api()` | 注册插件 API | 返回 None | `ValueError`: 插件不存在 |
| `call_plugin_method()` | 跨插件调用 | 返回方法返回值 | `ValueError`/`RuntimeError` |
| `get_plugin_api()` | 获取插件 API 信息 | 返回 Dict 或 None | - |
| `get_all_apis()` | 获取所有 API | 返回 Dict | - |
| `get_all_function_tools()` | 获取所有 Function Tools (MCP/OpenAI格式) | 返回 List[Dict] | - |

### 5. LoggerManager (utils/logging_tools.py)

| 接口 | 功能 | 正常状态 | 错误状态 |
|-----|------|---------|---------|
| `debug()` | 调试日志 | 返回 None | - |
| `info()` | 信息日志 | 返回 None | - |
| `warning()` | 警告日志 | 返回 None | - |
| `error()` | 错误日志 | 返回 None | - |
| `critical()` | 严重错误日志 | 返回 None | - |

> 签名说明：各级方法签名为 `info(module_name, message)`——第一参数是模块名，第二参数才是日志内容；插件侧通常直接使用注入的 `services.logger`（已绑定模块名）。

### 6. IPlugin 基类（抽象接口 `core/interfaces/i_plugin.py`，框架实现 `core/plugin/plugin_interface.py`）

| 属性/方法 | 功能 |
|----------|------|
| `plugin_name` | 插件名称（支持 `\n` 换行） |
| `plugin_id` | 插件 UUID（加载后赋值） |
| `_create_widget()` | 创建 UI 组件 |
| `on_plugin_loaded()` | 插件加载完成回调 |
| `skill_icon` | 技能图标 |
| `skill_description` | 技能描述 |

### 7. PluginServices 依赖注入（core/interfaces/plugin_services.py）

插件构造函数接收 `services: PluginServices`，经它获取全部框架服务（始终注入、无需自行实例化单例）：

| 字段 | 功能 |
|------|------|
| `data_provider` | 数据持久化与发布订阅 |
| `task_manager` | 后台任务管理 |
| `llm` | LLM 插件服务门面（ILLMService） |
| `font_manager` | 字体安装/卸载/预览 |
| `localization` | 插件取词门面（`tr(group, key, **params)`） |
| `logger` | 绑定插件模块名的日志器 |

---

## 安装说明

### 前置要求

- Python 3.14+
- Windows 10/11
- InstructionX 框架已安装

### 安装方法

#### 方法一：GitHub 安装（推荐）

1. 打开 InstructionX 应用
2. 进入「编辑 > 插件管理...」，在插件管理对话框中选择「从 GitHub 安装」
3. 输入插件仓库地址：
   ```
   https://github.com/KKPIP-Tech/instructionx-debug-plugin-cluster
   ```
4. 选择要安装的插件
5. 点击安装，插件将下载到 `plugin/` 目录

#### 方法二：手动安装

1. 克隆或下载本仓库
2. 复制所需插件目录到 InstructionX 安装目录：
   ```
   [InstructionX]/plugin/
   ├── [已有插件]/
   └── [新插件目录]/
   ```
3. 重启 InstructionX

#### 方法三：开发安装

作为 InstructionX 的兄弟目录克隆：

```
IX_For_Debug_Cluster/
├── InstructionX/          # 主框架
└── plugin/                # 本仓库（插件）
```

---

## 插件使用指南

详见 `blueprint_opencv/README.md` 与 `framework_api_demo/README.md`，其中 **Framework API Demo** 插件包含最详细的 API 文档。

---

## 开发指南

插件开发请遵循以下权威文档（本 README 不再内嵌代码示例，避免多源失真）：

- `PLUGIN_STRUCTURE_GUIDE.md` — 本插件集的目录结构、职责划分、导入、配置与文档规范；
- 框架仓库根目录 `AGENTS-for-PLUGIN-DEV.md` — 插件开发硬性规则（分层职责、导入规范、错误处理、设计模式等）；
- 框架仓库 `docs/core/plugin-system/plugin-development.md` — 从零开发插件的完整指南；
- 参考实现：`framework_api_demo/`（框架服务注入、i18n 取词、热重载清理的样板）。

### 最佳实践（要点）

1. **分层职责**：`entrance.py` 只做胶水层，业务逻辑在 `function/`，对外 API 在 `service.py`，UI 只做渲染与事件分发
2. **框架服务注入**：统一经构造函数注入的 `PluginServices` 获取框架服务，不自行实例化框架单例
3. **跨插件 API**：在 `information.py` 声明 `service_api` 并提供 `service.py`（类名以 `Service` 结尾），框架自动注册并同步为 MCP 工具，无需手动 `register_plugin_api`
4. **数据持久化**：使用 DataProvider，不用全局变量存需持久化的数据
5. **错误处理**：不裸 `except`、不静默吞异常；面向用户的错误弹窗 + 记日志
6. **线程安全**：阻塞操作放入后台任务（`register_async_task`）；工作线程回调更新 UI 须经 `utils.thread_utils` 封送
7. **多语言（可选）**：提供 `text/<语言代码>.xml` 语言包，经 `services.localization` 取词；IXPlugin.json 的 `name`/`description` 支持多语言字典

---

## 文件结构

```
plugin/
├── IXRepo.json                          # 仓库配置（定义 3 个插件）
├── PLUGIN_STRUCTURE_GUIDE.md            # 插件结构规范
├── README.md                            # 本文件
│
├── blueprint_opencv/                    # 蓝图节点化 OpenCV 图像处理
│   ├── entrance.py                      # 入口（胶水层）
│   ├── service.py                       # 对外接口层
│   ├── information.py                   # 插件元数据
│   ├── function/                        # 业务逻辑（节点目录/执行引擎）
│   ├── ui/                              # 视图层（蓝图画布/列表面板）
│   ├── config/                          # 配置文件
│   ├── text/                            # 语言包（zh.xml / en.xml）
│   ├── assets/                          # 示例图片
│   ├── docs/                            # 插件文档（PRD/SPEC）
│   └── IXPlugin.json
│
├── framework_api_demo/                  # 框架 API 演示（含详细 README）
│   ├── entrance.py                      # 入口（胶水层）
│   ├── service.py                       # 对外接口层
│   ├── information.py                   # 插件元数据
│   ├── function/                        # 业务逻辑
│   ├── ui/                              # 视图层
│   ├── config/                          # 配置文件
│   ├── text/                            # 语言包（zh.xml / en.xml）
│   ├── assets/                          # 资源文件
│   ├── icons/                           # 图标资源
│   ├── docs/                            # 插件文档（PRD/SPEC/实现文档）
│   ├── IXPlugin.json
│   └── README.md                        # API 详细文档
│
└── ui_demo/                             # UIKit 组件演示
    ├── entrance.py                      # 入口（胶水层）
    ├── service.py                       # 对外接口层
    ├── information.py                   # 插件元数据
    ├── function/                        # 业务逻辑（含组件目录）
    ├── ui/                              # 视图层（pages/ 各组件演示页）
    ├── config/                          # 配置文件
    ├── text/                            # 语言包（zh.xml / en.xml）
    ├── docs/                            # 插件文档（PRD/SPEC）
    └── IXPlugin.json
```

---

## License

本仓库为 InstructionX 官方插件集，许可条款与 InstructionX 主仓库保持一致，请参阅主仓库的 [LICENSE](https://github.com/KKPIP-Tech/InstructionX/blob/main/LICENSE) 文件。

---

## 相关链接

- [InstructionX Framework](https://github.com/KKPIP-Tech/InstructionX)
- [Plugin Development Guide](https://github.com/KKPIP-Tech/InstructionX/blob/main/docs/core/plugin-system/plugin-development.md)

---

*Built with PySide6 - Powered by InstructionX*
