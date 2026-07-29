# PRD：task_manager UI 迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

task_manager 插件 UI 依赖已删除的 `utils.style_qss`（`entrance.py` 顶层导入 `QssRegistry`），在当前框架（Alpha 1.0.3）下插件加载期即 ImportError，整个插件不可用。本次将其 UI 迁移至 InstructionX_UIKit 组件体系，恢复插件可用性。

## 2. 功能需求

- F1：删除 `entrance.py` 的 `utils.style_qss` 导入与 `_load_plugin_style`/`setStyleSheet` 样板，删除 `style/` 目录；
- F2：原生控件替换为 UIKit 组件：`QPushButton`→`Button(variant=...)`、`QListWidget`→`ListWidget`、`QComboBox`→`ComboBox`；
- F3：`QMessageBox` 结果告知类调用替换为 `Message.info/warning/error(parent, text)` 轻提示；删除确认的 `QMessageBox.question` 替换为 UIKit `Dialog.confirm(...)` 非阻塞确认；
- F4：添加任务的 `QInputDialog.getText` 替换为 `Dialog` + `LineEdit` 组合（模态 exec 获取输入）；
- F5：标题文字字号取 `T("font.lg")` 令牌，不再依赖失效的 `TaskManagerWidget[heading="true"]` QSS 选择器；
- F6：业务逻辑、DataProvider 键（tasks/statistics/last_event）、publish/subscribe、`service_api`、`self._plugin_id` 赋值一律不变。

## 3. 非功能需求

- import 全部置顶；ui/ 无业务逻辑；函数不超过 20 行；
- 版本号升至 `release.1.1.0`（IXPlugin.json 与 information.py 同步）；
- IXPlugin.json description 原为乱码，重写为简洁中文；
- 删除插件下全部 `__pycache__`。

## 4. 插件类型判断

单插件（插件集成员），id `task-manager`，仅 UI 迁移，无结构变化。
