# PRD：background_task_demo UI 迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

background_task_demo 插件依赖已删除的 `utils.style_qss`（`entrance.py` 顶层导入 `QssRegistry`），在当前框架（Alpha 1.0.3）下插件加载期即 ImportError，整个插件不可用。本次将其 UI 迁移至 InstructionX_UIKit 组件体系，恢复插件可用性，并顺带修复任务状态图标乱码问题。

## 2. 功能需求

- F1：删除 `entrance.py` 的 `QssRegistry` 导入与 `_load_plugin_style`/`setStyleSheet` 样板，删除 `style/` 目录（其 `QLabel[heading="true"]` 无前缀全局选择器本就不合规）；
- F2：`entrance.py` 定时任务回调中的 `except Exception: pass` 补上 `LoggerManager` 日志（`utils.logging_tools` 的 `LoggerManager` + `get_name`，import 置顶）；SignalBridge 线程封送机制保留不动；
- F3：原生控件替换为 UIKit 组件：`QPushButton`→`Button`（「创建任务」主操作 `variant="primary"`）、`QListWidget`→`ListWidget`、`QComboBox`→`ComboBox`、`QLineEdit`→`LineEdit`、`QSpinBox`→`SpinBox`、`QCheckBox`→`CheckBox`、`QTextEdit`→`TextArea`（日志区使用 `QFont(MONO_FAMILY)` 等宽字体）；`QMessageBox`×4→`Message.warning(self, text)`；
- F4：标题文字字号取 `T("font.lg")` 令牌，插件 UUID 标签颜色取 `T("color.text.secondary")` 令牌，替代旧 QSS `heading`/`muted` 选择器；
- F5：修复 `_get_status_icon` 乱码图标：pending→"⏳"、running→"▶"、completed→"✅"、failed→"❌"、cancelled→"⏹"（仅映射实际存在的状态键）；
- F6：业务逻辑、BackgroundTaskManager 调用、`service_api`（13 个方法）、任务工厂注册一律不变。

## 3. 非功能需求

- import 全部置顶（标准库→第三方→本地分组）；ui/ 无业务逻辑；函数 ≤20 行；注释与 docstring 使用中文；
- 版本号升至 `release.1.1.0`（IXPlugin.json 与 information.py 同步）。

## 4. 插件类型判断

单插件（插件集成员），id `background-task-demo`，仅 UI 迁移，无结构变化。
