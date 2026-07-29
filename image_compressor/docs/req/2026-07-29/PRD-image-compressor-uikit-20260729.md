# PRD：image_compressor UI 迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

image_compressor 插件 UI 依赖已删除的 `utils.style_qss`（`ui/main_widget.py` 顶层导入 `QssRegistry`），在当前框架（Alpha 1.0.3）下打开界面即 ImportError；且插件 `style/main.qss` 为整套硬编码深色主题（#1e1e1e 等），无法跟随全局亮/暗主题。本次将其 UI 迁移至 InstructionX_UIKit 组件体系，恢复插件可用性并接入全局主题。

## 2. 功能需求

- F1：删除 `utils.style_qss` 导入与 `_load_plugin_style`/`_unload_style`/`setStyleSheet` 样板，整体删除 `style/` 目录（含自绘 QSlider groove/handle 的硬编码深色 QSS）；
- F2：原生控件替换为 UIKit 组件：`QLineEdit`→`LineEdit`（带 clearable）、`QPushButton`→`Button`（主操作「压缩图片」用 `variant="primary"`）、`QSlider`→`Slider`；
- F3：3 处 `QMessageBox` 替换为 `Message.warning/success/error(self, text)`；`QFileDialog` 保留（系统文件对话框，无 UIKit 替代）；
- F4：标题文字字号取 `T("font.lg")` 令牌，不再依赖 QSS `heading` 属性选择器；
- F5：业务逻辑（`compress_image`/`get_image_info`）、`service_api`、`config/` 配置项不变。

## 3. 非功能需求

- import 全部置顶；ui/ 无业务逻辑；函数不超过 20 行；界面随全局亮/暗主题自动换肤；版本号升至 `release.1.1.0`（IXPlugin.json 与 information.py 同步）。

## 4. 插件类型判断

单插件（插件集成员），id `image-compressor`，仅 UI 迁移，无结构变化。
