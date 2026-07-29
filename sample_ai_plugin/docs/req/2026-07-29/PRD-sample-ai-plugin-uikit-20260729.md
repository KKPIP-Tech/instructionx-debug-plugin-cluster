# PRD：sample_ai_plugin UI 迁移至 InstructionX_UIKit + LLM 契约修复

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

sample_ai_plugin 插件在当前框架（Alpha 1.0.3）下存在两类失效：

1. UI 依赖已删除的 `utils.style_qss`（`ui/main_widget.py` 顶层导入 `QssRegistry`），打开界面即 ImportError；
2. 两处 LLM 契约破坏（P1）：`LLMPluginService.get_available_providers()` 已从框架删除；`ToolCallExecutor.chat_with_tools()` 返回值已由三元组改为结构化 `ToolChatResult`。

本次将 UI 迁移至 InstructionX_UIKit 组件体系并修复上述契约破坏，恢复插件可用性。

## 2. 功能需求

- F1：删除 `utils.style_qss` 导入与 `_load_plugin_style`/`setStyleSheet` 样板（含用 `config/default.json` ui 段做 `{key}` 二次替换的逻辑），删除 `style/` 目录（其 `#mainWidget` 等选择器与代码 objectName 不匹配，本就无效）；
- F2：原生控件替换为 UIKit 组件：`QPushButton`→`Button(variant="primary")`、`QComboBox`→`ComboBox`、`QTextEdit`→`TextArea`；标题字号取 `T("font.lg")` 令牌；
- F3（P1）：`CoreService.get_available_providers()` 内部改调 `self._llm.list_providers()`（返回 `List[ProviderInfo]`）；UI 侧读取 `ProviderInfo.name`/`.instance_id`/`.models`/`.current_chat_model` 与 `ModelInfo.name`/`.id`，下拉框 itemData 存**实例 id**（provider 参数语义：实例 id，`"default"` 表示默认实例）；
- F4（P1）：`chat_with_tools()` 返回值按 `ToolChatResult` 读取：`tool_results`（元素为 `ToolResult`，字段 `tool_name`/`result`）与 `final_text`；
- F5（P2）：`_on_sync_chat` 与 `_send_tools_request` 的裸 `threading.Thread` 内的 UI 更新改经 `utils.thread_utils.run_in_ui_thread` 封送；流式路径的 QThread+Signal 机制不变；
- F6：`core_service.py`（`register_sample_tools`）与 `llm_tools.py`（`datetime`）的函数级 import 移至文件顶部。

## 3. 非功能需求

- import 全部置顶；ui/ 无业务逻辑；版本号升至 `release.1.1.0`（IXPlugin.json 与 information.py 同步）。

## 4. 明确不做

- `function/tools/llm_tools.py` 的 `eval()` 安全隐患与 `_ensure_conversation` 逻辑缺陷为已知问题，本次不处理；
- 其余业务逻辑、`service_api`、`config/` 目录不变。

## 5. 插件类型判断

单插件（插件集成员），id `sample-ai-plugin`，UI 迁移 + 契约修复，无结构变化。
