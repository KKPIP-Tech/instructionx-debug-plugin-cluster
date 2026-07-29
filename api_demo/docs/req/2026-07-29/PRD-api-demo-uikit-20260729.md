# PRD：api_demo UI 迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

api_demo 插件 UI 依赖已删除的 `utils.style_qss`（`ui/main_widget.py` 顶层导入 `QssRegistry`、`entrance.py` 函数级导入 `get_style_qss`），在当前框架（Alpha 1.0.3）下打开界面即 ImportError。本次将其 UI 迁移至 InstructionX_UIKit 组件体系，恢复插件可用性。

## 2. 功能需求

- F1：删除全部 `utils.style_qss` 导入（含 `entrance.py` 的 `get_widget` 主题缓存覆写，覆写整体删除）、`_load_style`/`_on_destroyed` 样板与 `style/` 目录；
- F2：原生控件替换为 UIKit 组件：`QPushButton`→`Button(variant=...)`、`QListWidget`→`ListWidget`、`QTextEdit`→`TextArea`、`QMessageBox`→`Message.warning(parent, text)`；`QSplitter` 保留；
- F3：标题文字字号取 `T("font.lg")` 令牌，不再依赖失效的 `class="heading"` QSS 属性选择器；
- F4：业务逻辑（跨插件 API 调用）、`service_api`、`self._services.data_provider` 使用一律不变。

## 3. 非功能需求

- import 全部置顶；ui/ 无业务逻辑；函数 ≤20 行；版本号升至 `release.1.1.0`（IXPlugin.json 与 information.py 同步）；
- IXPlugin.json description 重写为简洁中文（原意：演示 PluginManager 跨插件 API 注册与调用）。

## 4. 插件类型判断

单插件（演示插件），id `api-demo`，仅 UI 迁移，无结构变化。
