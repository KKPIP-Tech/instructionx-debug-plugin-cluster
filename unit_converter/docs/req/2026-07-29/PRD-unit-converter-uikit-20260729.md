# PRD：unit_converter UI 迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

unit_converter 插件 UI 依赖已删除的 `utils.style_qss`（`ui/main_widget.py` 顶层导入 `QssRegistry`），在当前框架（Alpha 1.0.3）下打开界面即 ImportError。本次将其 UI 迁移至 InstructionX_UIKit 组件体系，恢复插件可用性。

## 2. 功能需求

- F1：删除 `utils.style_qss` 导入与 `_load_plugin_style`/`_on_destroy` 样板，删除 `style/` 目录；
- F2：原生控件替换为 UIKit 组件：`QLineEdit`→`LineEdit`（clearable）、`QPushButton`→`Button(variant="primary")`、`QComboBox`→`ComboBox`；
- F3：`QMessageBox` 数值校验警告 → `Message.warning`（非阻塞轻提示）；
- F4：标题与结果标签字号取 `T("font.lg")` 令牌并加粗，替代失效的 `heading`/`#resultValue` QSS 选择器；
- F5：业务逻辑（换算系数与计算）、`service_api`、`config/` 配置不变；`IXPlugin.json` 乱码 description 重写为简洁中文。

## 3. 非功能需求

- import 全部置顶；ui/ 无业务逻辑；函数 ≤ 20 行；版本号升至 `release.1.1.0`（IXPlugin.json 与 information.py 同步）。

## 4. 插件类型判断

单插件（插件集成员），id `unit-converter`，仅 UI 迁移，无结构变化。
