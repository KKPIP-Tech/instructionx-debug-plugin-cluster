# PRD：color_converter UI 迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

color_converter 插件 UI 依赖已删除的 `utils.style_qss`（`ui/main_widget.py` 顶层导入 `QssRegistry`），在当前框架（Alpha 1.0.3）下打开界面即 ImportError。本次将其 UI 迁移至 InstructionX_UIKit 组件体系，恢复插件可用性。

## 2. 功能需求

- F1：删除 `utils.style_qss` 导入与 `_load_plugin_style`/`_on_destroyed` 样板，删除 `style/` 目录；
- F2：原生控件替换为 UIKit 组件：`QLineEdit`→`LineEdit`（输入框带 clearable）、`QPushButton`→`Button(variant="primary")`；
- F3：标题文字字号取 `T("font.lg")` 令牌，不再依赖失效的 `ColorConverterWidget[heading="true"]` QSS 选择器；
- F4：业务逻辑（`hex_to_rgb`）、`service_api`、配置项不变。

## 3. 非功能需求

- import 全部置顶；ui/ 无业务逻辑；版本号升至 `release.1.1.0`（IXPlugin.json 与 information.py 同步）。

## 4. 插件类型判断

单插件（插件集成员），id `color-converter`，仅 UI 迁移，无结构变化。
