# PRD：task_reporter UI 迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

task_reporter 插件 UI 依赖已删除的 `utils.style_qss`（`ui/main_widget.py` 顶层导入 `QssRegistry`，`entrance.py` 函数级导入 `get_style_qss` 做主题缓存覆写），在当前框架（Alpha 1.0.3）下打开界面即 ImportError。本次将其 UI 迁移至 InstructionX_UIKit 组件体系，恢复插件可用性。

## 2. 功能需求

- F1：删除全部 `utils.style_qss` 导入（顶层 + 函数级）、`get_widget` 主题缓存覆写、`_load_stylesheet`/`_unload_stylesheet` 样板与 `style/` 目录；
- F2：原生控件替换为 UIKit 组件：`QPushButton`→`Button(variant=...)`、`QListWidget`→`ListWidget`、`QComboBox`→`ComboBox`、`QTextEdit`→`TextArea`；
- F3：结果告知类 `QMessageBox` → `Message.info/warning`；清除历史确认 `QMessageBox.question` → UIKit `Dialog.confirm`；修改 ID 的 `QInputDialog` → `Dialog` + `LineEdit`；
- F4：标题文字字号取 `T("font.lg")` 令牌，不再依赖失效的 `[heading="true"]` QSS 选择器；
- F5：业务逻辑（Service 调用、DataProvider subscribe/publish 键 statistics/last_event/event_log）、`service_api`、QTimer 定时刷新机制不变。

## 3. 非功能需求

- import 全部置顶（`ui/main_widget.py` 原函数级 `import json` 移至文件顶部）；ui/ 无业务逻辑；函数 ≤20 行；
- 版本号升至 `release.1.1.0`（IXPlugin.json 与 information.py 同步）；IXPlugin.json 乱码 description 重写为简洁中文。

## 4. 插件类型判断

单插件（插件集成员），id `task-reporter`，仅 UI 迁移，无结构变化。
