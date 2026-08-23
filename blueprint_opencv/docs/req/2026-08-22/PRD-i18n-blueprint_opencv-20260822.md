# PRD — blueprint_opencv 多语言（i18n）改造

- 创建日期：2026-08-22
- 修改日期：2026-08-22
- 插件：blueprint_opencv（Blueprint OpenCV，release.1.0.3，版本不变）
- 依赖框架能力：dev_i18n 分支 i18n 子系统（`PluginServices.localization` 注入的 `ILocalizationFacade`、插件 `text/<语言代码>.xml` 自动扫描注册、`LanguageManager.language_changed` / `plugin_language_changed` 信号）

## 1. 概述

blueprint_opencv 当前全部用户可见文案（工具条按钮、面板分区标题、存档/节点列表、参数面板表单标签、预览面板提示、对话框、节点类型显示名/分类/引脚名/参数标签）均为硬编码中文。框架 dev_i18n 分支新增插件级 i18n 子系统后，本插件需接入该子系统，提供 zh + en 双语言，并跟随框架语言切换实时刷新界面。

**价值**：

- 英文界面用户可正常使用全部功能（节点菜单、参数表单、对话框均显示英文）；
- 作为官方样板插件，示范「蓝图类插件如何接入插件 i18n」的标准做法；
- zh.xml 作为回退终点，保证任何情况下界面不出现取词失败占位符。

## 2. 用户故事

- 作为英文界面用户，我希望节点创建菜单、节点标题、参数表单显示英文，以便理解各节点用途。
- 作为切换界面语言的用户，我希望切换后插件界面立即以新语言显示，无需重启应用或重载插件。
- 作为中文用户，我希望插件行为与改造前完全一致（文案、功能、存档格式不变）。
- 作为跨插件 API / MCP 调用方，我希望 service_api 的返回结构与错误文案语义不变（错误仍为中文，见 SPEC §5 决策）。

## 3. 功能需求

- F1：插件提供 `text/zh.xml` 与 `text/en.xml` 两份语言文件，group/键集合完全一致；zh.xml 覆盖插件全部取词键（回退终点）。
- F2：entrance 经既有 `_get_services()` 模式获取 `services.localization`（判空），注入 MainWidget 与节点类型注册流程。
- F3：UI 各控件（MainWidget / ToolBar / GraphListPanel / NodeListPanel / PropertyPanel / PreviewPanel / node_bootstrap）的全部用户可见静态文案改为经 `ILocalizationFacade.tr()` 取词；门面未注入时优雅降级返回键名。
- F4：节点类型元数据（标题/描述/分类/引脚名）在 UI 展示边界（注册进 UIKit NodeRegistry 时）翻译；参数表单标签在属性面板重建表单时翻译；function 层数据结构与 service_api 语义不变。
- F5：MainWidget 连接 `language_changed` 与 `plugin_language_changed`（比对本插件 UUID）信号，集中实现 `_retranslate_ui()` 重设全部静态文案，并触发节点类型按新语言重注册、属性面板表单重建、存档/节点列表行刷新。
- F6：动态生成的文案（状态栏消息、列表行元信息、对话框内容）在生成时取词，无需回溯刷新。
- F7：IXPlugin.json 的 `name` / `description` 改为多语言字典（zh 沿用现有文案，en 新译）；版本号与其余字段不变。
- F8：日志文案（LoggerManager）保持中文不国际化；异常 message、choice 选项值（图序列化数据）、service_api 返回的错误文案不提取。

## 4. 非功能需求

- N1：向后兼容——MainWidget / 各面板 / `ensure_node_types_registered` 新增参数均有默认值 `None`，既有调用与测试不受影响；无语言包 / 无门面时界面行为不退化（显示键名除外场景不存在于正常加载路径）。
- N2：工程约束——函数/方法 ≤ 20 行、嵌套 ≤ 3 层、无魔法数、import 全部文件顶部、ui/ 不写业务逻辑、function/ 不依赖 PySide6。
- N3：热加载安全——语言切换引发的节点类型重注册复用既有「先查后注册 + 同名异定义纠正」幂等机制。
- N4：可校验——`.venv/Scripts/python.exe scripts/check_i18n_completeness.py` 对本插件语言文件报告无缺失、无孤立键。

## 5. 插件类型判断

蓝图编辑器型插件（Widget + function 节点元数据）。节点显示元数据存放于 function/node_catalog.py 纯数据表，属于「元数据在 function 层组装为显示文本」场景，采用 UI 展示边界取词方案（详见 SPEC §4），不给 function 层传 i18n、不改 BlueprintOpenCVService 构造签名。

## 6. 描述文件清单

| 文件 | 动作 |
|------|------|
| `plugin/blueprint_opencv/text/zh.xml` | 新增（全部键，中文文案） |
| `plugin/blueprint_opencv/text/en.xml` | 新增（同键集合，英文翻译） |
| `plugin/blueprint_opencv/IXPlugin.json` | 修改（name/description 多语言字典） |
| `plugin/blueprint_opencv/entrance.py` | 修改（注入 localization） |
| `plugin/blueprint_opencv/ui/main_widget.py` | 修改（取词 + _retranslate_ui + 信号连接） |
| `plugin/blueprint_opencv/ui/toolbar.py` | 修改（取词 + retranslate） |
| `plugin/blueprint_opencv/ui/graph_list_panel.py` | 修改（取词 + retranslate） |
| `plugin/blueprint_opencv/ui/node_list_panel.py` | 修改（取词 + retranslate） |
| `plugin/blueprint_opencv/ui/preview_panel.py` | 修改（取词 + retranslate） |
| `plugin/blueprint_opencv/ui/property_panel.py` | 修改（取词 + retranslate） |
| `plugin/blueprint_opencv/ui/node_bootstrap.py` | 修改（注册载荷翻译） |
| `plugin/blueprint_opencv/docs/req/2026-08-22/PRD-…、SPEC-…` | 新增（本文档与配套 SPEC） |
