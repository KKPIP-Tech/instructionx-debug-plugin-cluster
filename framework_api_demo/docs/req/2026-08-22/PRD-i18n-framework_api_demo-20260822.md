# PRD — framework_api_demo 多语言（i18n）改造

- 创建日期：2026-08-22
- 修改日期：2026-08-22
- 插件：framework_api_demo（Framework API Demo，release.1.0.3，本任务不变更版本号）
- 关联框架分支：InstructionX dev_i18n（新增 i18n 子系统：插件语言包自动注册 + `PluginServices.localization` 取词门面）

## 1. 概述

### 1.1 解决的问题

framework_api_demo 的全部用户可见文案（按钮、分组标题、占位提示、结果面板标题、日志面板消息模板、演示服务返回的 message/error 文本等）均以中文字面量硬编码在源码中。框架 dev_i18n 分支已提供插件级多语言能力（`text/<语言代码>.xml` 语言包 + `ILocalizationFacade` 取词门面 + 实时语言切换信号），本插件尚未接入，英文界面用户将看到全中文界面。

### 1.2 价值

- 作为官方演示插件，率先落地插件 i18n 改造范式，为其余官方/第三方插件提供参考实现；
- 英文用户可获得完整英文界面，提升框架国际化形象；
- 文案集中收敛到语言文件，后续维护与增补语言（如 ja）成本显著降低。

## 2. 用户故事

- 作为**中文用户**，我希望插件界面与操作结果提示保持中文，且与改造前一致；
- 作为**英文用户**，我希望框架语言切换为 English 后，插件全部界面文案、结果标题、日志模板实时切换为英文；
- 作为**插件开发者**，我希望通过本插件的代码了解：语言包目录约定、门面注入方式、`_retranslate_ui()` 刷新模式、服务层取词方式。

## 3. 功能需求

| 编号 | 需求描述 |
|------|----------|
| FR-1 | 插件新增 `text/zh.xml` 与 `text/en.xml` 语言包，框架加载时自动扫描注册，插件不含任何登记代码 |
| FR-2 | zh.xml 覆盖插件全部用户可见文案键（回退终点，不得缺键）；en.xml 提供全部键的英文翻译；两文件 group 名与键名完全一致 |
| FR-3 | UI 层（main_widget + 6 个演示 Tab）全部用户可见硬编码文案改为经 `ILocalizationFacade.tr()` 取词：分组标题、按钮、表单标签、占位提示、结果面板标题、日志面板消息模板、Message 弹窗文案、API 文档展示文本 |
| FR-4 | 服务层（function/services + service.py 委托链）返回结果字典中面向用户展示的 message/error 文本、经 notifier 上抛到日志面板的事件模板，改为经 `services.localization` 取词 |
| FR-5 | entrance 经既有 `_get_services()` 模式取 `services.localization`（判空）注入 MainWidget，并逐级下传各 Tab |
| FR-6 | MainWidget 实现 `_retranslate_ui()`：connect `language_changed` 与 `plugin_language_changed`（比对本插件 UUID）两个信号，语言切换时重设全部用户可见文案（含各 Tab），不抛异常、不丢失已展示的结果历史 |
| FR-7 | 门面未注入的降级路径（独立测试、service.py 委托服务等场景）不显示裸键名：UI 层按约定返回键名，服务层回退中文默认文案 |
| FR-8 | IXPlugin.json 的 `name` 与 `description` 改为 `{"zh": ..., "en": ...}` 多语言字典形式，其余字段不动 |
| FR-9 | LoggerManager 日志、异常 message（`str(e)`）、纯内部标识符（任务类型、事件前缀协议、task_id 等）保持原样，不国际化 |

## 4. 非功能需求

- NFR-1 兼容性：不改版本号（release.1.0.3）；不改变 service_api 对外接口语义与发布订阅 key；构造函数新增参数均带默认值 `None`，向后兼容；
- NFR-2 代码约束：函数/方法 ≤ 20 行、嵌套 ≤ 3 层、无魔法数；import 全部置顶（标准库→第三方→本地），严禁函数级 import；插件内部相对导入，框架能力绝对导入（接口优先 `core.interfaces`）；
- NFR-3 语言切换刷新为就地重设文案，不重建整个 Widget 树、不清空结果面板与日志面板历史；
- NFR-4 校验：`scripts/check_i18n_completeness.py` 对插件语言包报告无缺失；全部改动 .py 通过 `py_compile`；offscreen 冒烟断言 zh/en 文案切换正确。

## 5. 插件类型判断

UI 型插件（含 Widget + 后台服务层）。i18n 接入点：`PluginServices.localization` 门面注入 UI 与服务两层；UI 层自行监听语言信号重翻译。

## 6. 描述文件清单

| 文件 | 变更 |
|------|------|
| `text/zh.xml` | 新增：全部用户可见文案的中文原文 |
| `text/en.xml` | 新增：全部键的英文翻译 |
| `IXPlugin.json` | `name` / `description` 改多语言字典；version 保持 release.1.0.3 |
| `information.py` | 不变更（service_api 描述为 API 契约文本，本任务不提取，见 SPEC 设计决策） |
| `entrance.py` | 注入 localization 门面与 plugin_id 到 MainWidget；启动日志取词 |
| `ui/main_widget.py` | 新增 i18n 参数、`_tr`、`_retranslate_ui()`、信号连接 |
| `ui/tabs/*.py`（7 个文件） | 各 Tab 新增 i18n 参数、`_tr`、`retranslate()`；文案全部取词 |
| `function/services/base.py` | 基类解析 localization 门面，提供服务层 `_tr`（带中文默认回退） |
| `function/services/*.py`（6 个服务） | 用户可见 message/error/notifier 模板取词 |
| `service.py` | 不变更（无门面注入路径，详见 SPEC 设计决策 D4） |
| `docs/req/2026-08-22/PRD-*.md` / `SPEC-*.md` | 本文档与对应技术方案 |
