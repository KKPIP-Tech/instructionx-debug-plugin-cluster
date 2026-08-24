# PRD：双 Service 实例共享管线运行态

- 创建日期：2026-08-24
- 修改日期：2026-08-24

## 概述

框架的跨插件 API 自动注册机制（`core/plugin/manager.py` `_auto_register_plugin_api`）会自行实例化第二个 `BlueprintOpenCVService`，与 entrance 为 UI 创建的实例并存。修复前两个实例各自持有 `PipelineController` 与图快照，导致跨插件 / MCP 调用与 UI 完全脱节：`run_pipeline` 永远跑空图、`save_graph` 以空图覆盖用户存档（数据损坏）、`load_graph` / `get_last_result_info` 对 UI 不可见。

## 用户故事

- 作为 MCP / 跨插件调用方，我希望 `save_graph` / `run_pipeline` 操作的是用户在画布上真实编辑的图，而不是一份空运行态；
- 作为插件用户，我不希望外部调用把我的存档覆盖成空图。

## 功能需求

1. FR-1：同一插件的全部 Service 实例共享同一份管线运行态（PipelineController + 图快照）；
2. FR-2：跨实例并发提交运行时由运行状态机正确拦截（「已有运行中的管线」）；
3. FR-3：插件卸载时共享运行实例被显式清理，热重载后干净重建；
4. FR-4（顺带）：运行失败时状态栏与日志显示错误的 `message` 字段而非 dict 原文。

## 非功能需求

- 不触碰框架代码（插件侧修复）；
- 不改变 service_api 九个方法的签名与返回结构（向后兼容）；
- function 层保持无 PySide6 依赖。

## 插件类型与 ID

既有插件 `blueprint-opencv` 的缺陷修复，无新增描述文件。
