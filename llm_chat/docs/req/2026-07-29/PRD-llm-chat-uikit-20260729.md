# PRD：llm_chat UI 拆分与 InstructionX_UIKit 迁移

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

llm_chat 是全插件集最重的迁移对象：`entrance.py` 原 617+ 行 UI 构建与插件胶水层混杂，且依赖已删除的 `utils.style_qss`；同时其流式调用沿用旧版「返回值即 chunk 迭代器」契约，在当前框架（Alpha 1.0.3，`LLMProvider.stream_chat` 已改为 callback 契约并返回完整文本）下必然抛出 `AttributeError`，流式对话完全不可用。本次完成 UI 拆分、UIKit 迁移、流式契约修复与失效耦合清理，恢复插件可用性。

## 2. 功能需求

- F1（UI 拆分）：`entrance.py` 中全部 UI 构建/事件处理方法（约 30 个 `_build_*`/`_create_*`/`_on_*`）迁至 `ui/main_widget.py` 的 `MainWidget`；`ChatWorker(QThread)` 迁至 `ui/chat_worker.py`；`entrance.py` 只保留胶水层（`plugin_name`、`on_plugin_loaded`、`_create_widget` 创建 Service + MainWidget）。拆分为纯移动，不改变交互逻辑（除下列明确修复点）。
- F2（UIKit 迁移）：删除 `utils.style_qss` 导入、`get_widget` 主题缓存覆写、`_load_plugin_style`/`setStyleSheet` 样板与 `style/` 目录；原生控件替换为 UIKit 组件（映射见 SPEC）；`QMessageBox` 按语义替换为 `Message.info/warning/error` 或 `Dialog.confirm`/`Dialog.info`；`QFileDialog` 保留。
- F3（流式契约修复，P1）：`function/services/core_service.py` 的 `stream_send_message`/`_stream_iterate` 重构为适配框架 callback 契约（`callback(chunk_text, done)` + 返回完整文本），保持插件内 `ChatWorker` 的生成器消费方式不变。
- F4（失效耦合移除）：
  - 删除 `__app_llm__` 系统键读取，`get_current_llm_preference` 改为经 `get_llm_plugin_service().get_default_provider_id(feature="chat")` + `list_providers()` 的 `ProviderInfo.current_chat_model` 获取；
  - 删除主窗口信号耦合（`_find_main_window`/`llm_provider_changed`/`_on_global_llm_changed`，含函数级 `import ui.main_window`）；Provider 下拉框在 `_create_widget` 时填充一次，保留「刷新模型」手动刷新入口；
  - 删除 `self._plugin_id = "llm-chat-default"` 覆写，使用框架注入的 `plugin_id`（仅保留局部回退常量供独立实例化场景）；
  - 函数级 `import traceback` 等全部置顶。

## 3. 非功能需求

- import 全部置顶（标准库/第三方/本地分组）；`ui/` 不写业务逻辑；
- LLM 访问继续直用 `get_llm_provider()`（本次不做 llm_facade 全面替换）；同步 chat 路径（`response.content`/`.model`）不动；`service_api`、DataProvider PRIVATE 键不动；
- 版本号升至 `release.1.1.0`（IXPlugin.json 与 information.py 同步）。

## 4. 插件类型判断

单插件（插件集成员），id `llm-chat`，结构变化为新增 `ui/` 包、删除 `style/` 目录，对外接口不变。
