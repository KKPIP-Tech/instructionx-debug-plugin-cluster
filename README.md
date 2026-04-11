# InstructionX Official Plugins

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)](https://www.python.org/)
[![PySide6](https://img.shields.io/badge/PySide6-6.10+-green.svg)](https://doc.qt.io/qtforpython/)
[![License](https://img.shields.io/badge/License-Modified%20Apache%202.0-orange.svg)](#license)

**InstructionX 框架官方插件集合**

[English](./README_en.md) | 中文

</div>

---

## 项目简介

本仓库包含 **InstructionX 框架**的官方插件集合，共 14 个测试工具插件，涵盖文本处理、代码格式化、图片压缩、单位转换、任务管理、LLM 对话等功能。

### 主要特性

- **插件热插拔**：无需重启应用即可加载/卸载插件
- **框架 API 访问**：直接调用 DataProvider、BackgroundTaskManager、LLMProvider 等核心服务
- **MCP 协议支持**：插件可作为 MCP tools 暴露 API 供外部 LLM 调用
- **跨插件通信**：通过 PluginManager 实现插件间方法调用
- **PySide6 UI**：基于 Qt 的现代化用户界面

---

## 插件列表

### 工具类插件

| 插件 | ID | 描述 |
|------|-----|------|
| **String Tools** | `string-tools` | 文本处理工具集，包括大小写转换、文本反转、单词首字母大写、去空白、字符/单词计数 |
| **Text Formatting** | `text-formatting` | 文本大小写转换工具，支持批量处理 |
| **Color Converter** | `color-converter` | 颜色格式转换工具，支持 HEX 与 RGB 互转 |
| **Unit Converter** | `unit-converter` | 单位转换工具，支持长度（m, km, cm, mm, in, ft）、重量、温度等 |

### 代码开发插件

| 插件 | ID | 描述 |
|------|-----|------|
| **Code Formatter** | `code-formatter` | 代码格式化工具，支持 JSON/XML 格式化、注释移除、代码压缩 |
| **API Demo** | `api-demo` | 演示 PluginManager API 调用，展示如何发现和调用其他插件的 API |

### 任务管理插件

| 插件 | ID | 描述 |
|------|-----|------|
| **Task Manager** | `task-manager` | 任务管理工具，支持 CRUD 操作、状态跟踪（pending, in_progress, completed, cancelled）、数据持久化 |
| **Task Reporter** | `task-reporter` | 任务统计报表工具，实时订阅任务变化，支持 JSON/TXT/HTML 多格式导出 |

### LLM/AI 插件

| 插件 | ID | 描述 |
|------|-----|------|
| **LLM Chat** | `llm-chat` | 多 Provider LLM 对话工具，支持 MiniMax、SiliconFlow、GLM、Ollama，提供流式输出、多会话管理、图片输入（多模态） |
| **Sample AI Plugin** | `sample-ai-plugin` | 演示 LLMPluginService 集成，包括会话创建、同步/流式消息发送、工具调用 |

### 系统/框架插件

| 插件 | ID | 描述 |
|------|-----|------|
| **Framework API Demo** | `framework-api-demo` | 框架所有核心 API 的完整演示，包括 DataProvider、BackgroundTaskManager、LLMProvider、PluginManager、LoggerManager |
| **Background Task Demo** | `background-task-demo` | BackgroundTaskManager 完整演示，包括同步任务、异步任务、定时任务、任务回调 |
| **UI Demo** | `ui-demo` | PySide6/Qt 控件展示，包括按钮、输入框、复选框、单选按钮、滑块、进度条、下拉框等 |
| **Local Server** | `local-server` | 本地 HTTP 服务器，用于接收 webhooks，支持 GET/POST 请求、日志记录、长期任务集成 |
| **Image Compressor** | `image-compressor` | 图片压缩工具，支持质量调节、图片信息查看 |

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
| `register_sync_task()` | 注册同步任务 | 返回 task_id | - |
| `register_async_task()` | 注册异步任务 | 返回 task_id | - |
| `register_scheduled_task()` | 注册定时任务 | 返回 task_id | - |
| `register_long_running_task()` | 注册长期任务 | 返回 task_id | - |
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

### 6. IPlugin 基类 (core/plugin/plugin_interface.py)

| 属性/方法 | 功能 |
|----------|------|
| `plugin_name` | 插件名称（支持 `\n` 换行） |
| `plugin_id` | 插件 UUID（加载后赋值） |
| `_create_widget()` | 创建 UI 组件 |
| `on_plugin_loaded()` | 插件加载完成回调 |
| `skill_icon` | 技能图标 |
| `skill_description` | 技能描述 |

---

## 安装说明

### 前置要求

- Python 3.14+
- Windows 10/11
- InstructionX 框架已安装

### 安装方法

#### 方法一：GitHub 安装（推荐）

1. 打开 InstructionX 应用
2. 进入 `Edit` > `Install GitHub Plugin`
3. 输入插件仓库地址：
   ```
   https://github.com/KKPIP-Tech/InstructionX-Plugins
   ```
4. 选择要安装的插件
5. 点击 Install，插件将下载到 `plugin/` 目录

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

详见各插件目录下的 `README.md`，其中 **Framework API Demo** 插件包含最详细的 API 文档。

---

## 开发指南

### 创建新插件

#### 1. 创建插件目录结构

```
plugin/
└── my_awesome_plugin/
    ├── __init__.py
    ├── entrance.py
    ├── service.py
    └── IXPlugin.json
```

#### 2. 编写 IXPlugin.json

```json
{
    "id": "my-awesome-plugin",
    "name": "My Awesome Plugin",
    "version": "release.1.0.0",
    "main": "entrance.py",
    "description": "一个很棒的插件",
    "author": "Your Name",
    "author_email": "you@example.com",
    "homepage": "https://github.com/KKPIP-Tech/InstructionX",
    "keywords": ["instructionx", "plugin", "awesome"],
    "dependencies": {}
}
```

#### 3. 编写 service.py

```python
"""业务逻辑层"""

class MyService:
    def __init__(self, plugin_id):
        self.plugin_id = plugin_id

    def do_awesome_thing(self, input_text: str) -> str:
        """主要功能"""
        return input_text.upper()

    def register_api(self) -> dict:
        """返回 API 方法供跨插件调用"""
        return {
            "do_awesome_thing": self.do_awesome_thing
        }
```

#### 4. 编写 entrance.py

```python
"""插件入口 - UI 实现"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from core.plugin.plugin_interface import IPlugin

class MyAwesomePlugin(IPlugin):
    @property
    def plugin_name(self) -> str:
        return "My\nAwesome"

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        self.service = MyService(self.plugin_id)

        widget = QWidget(parent)
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel("My Awesome Plugin"))

        self.input_text = QTextEdit()
        layout.addWidget(self.input_text)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)

        btn = QPushButton("Do Awesome Thing")
        btn.clicked.connect(self._on_button_clicked)
        layout.addWidget(btn)

        return widget

    def _on_button_clicked(self):
        input_data = self.input_text.toPlainText()
        result = self.service.do_awesome_thing(input_data)
        self.output_text.setText(result)

    def on_plugin_loaded(self):
        from core.plugin.manager import PluginManager
        pm = PluginManager()
        pm.register_plugin_api(self.plugin_id, self.service.register_api())
```

#### 5. 测试插件

1. 将插件目录复制到 `[InstructionX]/plugin/`
2. 启动 InstructionX
3. 在技能面板中找到插件并测试

### 最佳实践

1. **分离 UI 与逻辑**：业务逻辑放在 `service.py`，UI 放在 `entrance.py`
2. **使用 DataProvider 持久化**：不要使用全局变量存储需要持久化的数据
3. **优雅处理错误**：用 try/except 包装 API 调用
4. **记录重要事件**：使用 LoggerManager 进行调试日志
5. **插件 ID 一致性**：使用与 `IXPlugin.json` 相同的 ID 格式
6. **线程安全**：长时间运行的操作使用 QThread，通过信号更新 UI
7. **资源清理**：如需要，在析构函数中清理资源

---

## 文件结构

```
plugin/
├── IXRepo.json                          # 仓库配置（定义所有 14 个插件）
│
├── api_demo/                            # API 调用演示
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── background_task_demo/                # 后台任务演示
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── code_formatter/                      # 代码格式化
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── color_converter/                     # 颜色转换
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── framework_api_demo/                  # 框架 API 演示（含详细 README）
│   ├── entrance.py
│   ├── service.py
│   ├── information.py
│   ├── IXPlugin.json
│   └── README.md                       # API 详细文档
│
├── image_compressor/                   # 图片压缩
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── llm_chat/                            # LLM 对话
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── local_server/                       # 本地服务器
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── sample_ai_plugin/                   # AI 插件示例
│   ├── entrance.py
│   ├── tools.py
│   ├── __init__.py
│   └── IXPlugin.json
│
├── string_tools/                       # 字符串工具
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── task_manager/                       # 任务管理
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── task_reporter/                      # 任务报表
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── text_formatting/                    # 文本格式化
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
├── ui_demo/                            # UI 控件演示
│   ├── entrance.py
│   ├── service.py
│   └── IXPlugin.json
│
└── unit_converter/                     # 单位转换
    ├── entrance.py
    ├── service.py
    └── IXPlugin.json
```

---

## License

本项目基于 **Modified Apache License 2.0** 许可证。

详细信息请参阅 InstructionX 主仓库的 [LICENSE](https://github.com/KKPIP-Tech/InstructionX/blob/main/LICENSE) 文件。

---

## 相关链接

- [InstructionX Framework](https://github.com/KKPIP-Tech/InstructionX)
- [Plugin Development Guide](https://github.com/KKPIP-Tech/InstructionX/blob/main/docs/core/plugin-system/plugin-development.md)

---

*Built with PySide6 - Powered by InstructionX*
