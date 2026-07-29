# PRD：string_tools UI 迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

string_tools 插件 UI 依赖已删除的 `utils.style_qss`（`ui/main_widget.py` 顶层导入 `QssRegistry`、`entrance.py` 函数级导入 `get_style_qss` 并覆写 `get_widget` 做主题缓存），在当前框架（Alpha 1.0.3）下打开界面即 ImportError。本次将其 UI 迁移至 InstructionX_UIKit 组件体系，恢复插件可用性。

## 2. 功能需求

- F1：删除全部 `utils.style_qss` 导入（含 `entrance.py` 的函数级导入与 `get_widget` 主题缓存覆写）、`_load_plugin_style`/`_on_destroyed` 样板与 `style/` 目录；
- F2：原生控件替换为 UIKit 组件：`QTextEdit`→`TextArea`（输出结果区使用 `QFont(MONO_FAMILY)` 等宽字体）、`QPushButton`→`Button`（文本变换等主操作使用 `variant="primary"`，「统计信息」使用默认变体）；
- F3：标题文字字号取 `T("font.lg")` 令牌，不再依赖失效的 heading QSS 选择器；统计标签的 `muted` 属性随 QSS 一并移除；
- F4：7 个字符串处理方法、`service_api`、`config/` 配置项一律不变。

## 3. 非功能需求

- import 全部置顶；ui/ 无业务逻辑；函数 ≤ 20 行；版本号升至 `release.1.1.0`（IXPlugin.json 与 information.py 同步）。

## 4. 插件类型判断

单插件（插件集成员），id `string-tools`，仅 UI 迁移，无结构变化。
