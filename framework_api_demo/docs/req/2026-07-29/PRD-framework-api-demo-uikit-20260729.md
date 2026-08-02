# PRD：framework_api_demo UI 拆分与迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

framework_api_demo 插件的 `entrance.py` 达 802 行，UI 构建（5 个演示 Tab）与
插件胶水逻辑混杂，且依赖已删除的 `utils.style_qss`（顶层导入 `QssRegistry`、
`get_widget` 内函数级导入 `get_style_qss`），在当前框架（Alpha 1.0.3）下打开
界面即 ImportError。本次完成三件事：

1. 把全部 UI 代码从 `entrance.py` 拆分到 `ui/main_widget.py`；
2. UI 迁移至 InstructionX_UIKit 组件体系；
3. 适配 `LLMProvider.get_models()` 返回类型变更（`Dict[str, List[ModelInfo]]`）。

## 2. 功能需求

- F1（UI 拆分）：`entrance.py` 中全部 UI 构建方法（`_build_widget_layout`/
  `_build_left_panel`/`_build_right_panel`/`_make_scroll_tab`/各 Tab 的
  `_build_*`/`_create_*`）与事件处理器（`_on_*`）、`_display_result`/`_log`
  迁至 `ui/main_widget.py` 的 `MainWidget`；`entrance.py` 只留胶水层
  （`plugin_name`、`on_plugin_loaded`、`_get_data_provider`、
  `_register_with_provider`、`_init_services`、`_create_widget`）；
  `SignalBridge` 保留。**纯移动，不改交互逻辑**（除 F2/F3 修复点）。
- F2（UIKit 迁移）：删除 `utils.style_qss` 相关导入、`get_widget` 主题缓存
  覆写、`_load_plugin_style`/`setStyleSheet` 样板与 `style/` 目录；原生控件
  替换为 UIKit 组件（Button/ComboBox/LineEdit/SpinBox/ListWidget/TextArea/
  Tabs）；结果与日志区使用 `QFont(MONO_FAMILY)` 等宽字体；`QMessageBox`×5
  替换为 `Message.info/warning(self, text)`；`_display_result` 内嵌 HTML 的
  硬编码颜色 `#EF4444`/`#10B981` 改为 `T("color.danger")`/`T("color.success")`
  令牌。
- F3（get_models 适配）：`LLMProvider.get_models(provider)` 现返回
  `Dict[str, List[ModelInfo]]`（键为提供商实例 id）。检查
  `function/services/core_service.py` 与 UI 中的消费点，按 Dict 语义适配；
  `get_cached_models` 返回 `List[ModelInfo]` 不变。
- F4：entrance.py 注册逻辑中按异常文案匹配 "已存在"/"exists" 的行为保持不变；
  DataProvider/BackgroundTaskManager/PluginManager 直用单例的方式不变；
  `service_api`（3 个方法）与 `config/` 不变。

## 3. 非功能需求

- import 全部置顶，删除未使用的 `uuid`/`get_name` 导入；
- `ui/` 中不写业务逻辑（仅调用已注入的 Service）；
- 版本号升至 `release.1.1.0`（information.py 与 IXPlugin.json 同步）；
- 删除插件下全部 `__pycache__`。

## 4. 插件类型判断

单插件（插件集成员），id `framework-api-demo`，UI 层结构性重构 + 框架 API
适配，业务服务层不变。
