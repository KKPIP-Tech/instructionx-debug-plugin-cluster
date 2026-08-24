# PRD：ui_demo 插件多国语言（i18n）适配

- **创建日期**：2026-08-22
- **修改日期**：2026-08-22

## 1. 概述

框架 dev_i18n 分支新增 i18n 子系统（`core/i18n`）：插件可提供 `text/<语言代码>.xml`
语言包，经 `PluginServices.localization` 注入的 `ILocalizationFacade` 门面取词，
并支持界面语言实时切换与每插件语言覆盖。

ui_demo（UIKit 组件橱窗）目前全部用户可见文案为硬编码中文（导航树、10 个分类、
80+ 演示页的标题/说明/分区/按钮/参数标签/演示数据、蓝图节点类型名与状态栏消息等，
约 5900 行 UI 代码），在英文界面下仍显示中文，且语言切换后不会刷新。

本次将插件全部用户可见文案提取到 `text/zh.xml`（回退终点，沿用现有中文）与
`text/en.xml`（完整英文翻译），并接入语言切换实时刷新，使橱窗在中英文界面下
均完整可读。

**核心价值**：作为插件开发者的 UI 参考橱窗，ui_demo 自身率先示范插件 i18n 的
标准接入方式；英文用户可正常使用全部演示页。

## 2. 用户故事

- 作为英文用户，我希望橱窗的导航树、页面标题、按钮与演示内容显示英文，以便理解每个组件的用途；
- 作为用户，我希望在「编辑 → 语言」切换界面语言后，橱窗立即以新语言重绘，无需重启应用或重开插件；
- 作为用户，我希望可以对 ui_demo 单独设置语言覆盖（插件语言对话框），橱窗只在自己的语言变化时刷新；
- 作为插件开发者，我希望 ui_demo 的源码可作为「插件如何接入 i18n」的参考范例。

## 3. 功能需求

- F1：新增 `text/zh.xml` 与 `text/en.xml`，覆盖插件全部用户可见硬编码文案
  （UI 标签、按钮、选项卡/导航树标题、分区标题、占位提示、tooltip、对话框文案、
  状态栏消息模板、蓝图节点类型显示名/描述/分类/引脚名/参数标签、演示数据文本）；
  两语言分组与键集合完全一致；
- F2：`entrance.py` 新增 `__init__(services=None)` 保存框架注入的 `PluginServices`
  （仿 framework_api_demo 的 `_get_services()` 模式：构造注入优先，回退 `_services`
  实例属性），创建 MainWidget 时传入 `services.localization` 与 `plugin_id`；
- F3：MainWidget 导航树分类/页标题经门面取词；`language_changed` 与
  `plugin_language_changed`（比对插件 UUID）信号触发 `_retranslate_ui()`：
  重设导航文案、清空页面缓存并按当前语言重建当前页；
- F4：全部页面工厂签名升级为 `create_page(i18n=None)`，页面内部经
  `bind_tr(i18n, group)` 闭包取词；门面未注入时优雅降级返回键名；
- F5：IXPlugin.json 的 `name`/`description` 改为多语言字典（`{"zh": ..., "en": ...}`），
  版本号保持 `release.1.0.3` 不变；
- F6：不提取的内容保持原样：LoggerManager 日志（本插件无）、异常 message、
  代码注释、USAGE 代码示例（代码即文档，不翻译）、纯内部标识符；
- F7：对外 API `get_control_list()` 行为与返回内容不变（`function/component_catalog.py`
  为 API 数据契约，非 UI 文案，不随界面语言变化）。

## 4. 非功能需求

- 兼容性：`MainWidget`/`create_page` 新参数全部带默认值 None，旧调用方式不破坏；
  service_api 语义、发布订阅 key、版本号均不变；
- 规范：中文注释/docstring、新代码 type hints、import 全部置顶
  （禁止函数级 import）、函数 ≤20 行、嵌套 ≤3 层、无魔法数；
- 性能：语言切换仅重建已缓存页面（懒加载语义不变）；未访问过的页面不产生开销；
- 可维护性：分组按页面模块划分、键名点分自解释；zh.xml 为回退终点必须完整。

## 5. 插件类型判断

- 单插件（插件集成员），id `ui-demo`，目录 `plugin/ui_demo/`；类型不变。

## 6. 描述文件清单

| 文件 | 变更 |
|---|---|
| `IXPlugin.json` | `name`/`description` 改为多语言字典；version 等其余字段不变 |
| `information.py` | 不变（版本保持 release.1.0.3；`plugin_name` 为英文品牌名保持不变） |
| `text/zh.xml`、`text/en.xml` | 新增语言包 |
| `IXRepo.json` | 不变（由仓库维护者统一处理） |
