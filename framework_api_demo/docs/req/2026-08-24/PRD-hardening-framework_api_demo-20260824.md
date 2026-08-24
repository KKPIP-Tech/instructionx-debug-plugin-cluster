# PRD — framework_api_demo 健壮性与新 API 覆盖优化（P0/P1/P2 批次）

- 创建日期：2026-08-24
- 修改日期：2026-08-25
- 插件：framework_api_demo（Framework API Demo，本任务不变更版本号）
- 对应 SPEC：`SPEC-hardening-framework_api_demo-20260824.md`

## 1. 概述

### 1.1 背景与问题

framework_api_demo 是框架官方 API 演示插件，承担「框架能力活文档」的职责。
本批次排查发现三类问题：

1. **P0 线程模型缺陷**：阻塞型 LLM/MCP/线程演示误用
   `register_sync_task`（在调用线程内联执行），UI 线程触发时直接卡死界面；
   `send_chat`/`send_embedding` 在 UI 线程裸发同步 HTTP 请求；
2. **P1 健壮性与可维护性缺陷**：`_load_config` 静默吞异常且每次调用重复读盘；
   多个函数超 20 行（职责混杂）；InfoTab 直连单例 `ThemeManager` 信号，
   热重载后残留连接可能触碰已销毁控件；Info Tab 未覆盖 FontManager 与
   i18n 门面两个只读子系统；
3. **P2 新 API 覆盖不足与杂项**：框架新增的 `stop_long_task(delete_from_storage=)`、
   `is_long_task_running`、`chat_with_tools_stream`、`stream_send_message(images=)`、
   模型 `capabilities` 能力标签等接口无演示；UI 布局魔法数散落；LLM 触发按钮
   无防重入；原始 JSON 用弹窗截断展示；MCP 远程连接卸载时不断开；
   data_service 订阅事件列表跨线程无锁。

### 1.2 价值

- 演示插件自身行为正确（不再卡 UI 线程、热重载安全），作为参考实现不出错示范；
- 覆盖框架全部新增公开接口，保持「活文档」完整性；
- 消除静默失败与资源泄漏，便于框架使用者照抄安全模式。

## 2. 用户故事

- 作为**插件开发者**，我点击任意 LLM 演示按钮时界面不冻结，且请求进行中
  按钮禁用、无法重复提交；
- 作为**插件开发者**，我热重载插件后不出现已销毁控件报错、不残留远程 MCP 连接；
- 作为**框架评估者**，我能在 Info/LLM/Task Tab 中直接看到 FontManager、
  i18n 门面、长期任务新语义、工具流式调用、多模态 images 参数等新接口的用法；
- 作为**维护者**，布局间距/限高集中在一处常量模块，改一处全局生效。

## 3. 功能需求

| 编号 | 需求描述 |
|------|----------|
| FR-1 | 全部阻塞型演示经 `register_async_task` 提交线程池（8 处），管理器关闭返回 None 时给出明确错误 |
| FR-2 | send_chat/send_embedding 改为后台任务 + notifier 事件上抛，UI 提供结果拉取展示 |
| FR-3 | `_load_config` 失败记 WARNING 日志；按 mtime 做模块级缓存避免重复读盘 |
| FR-4 | 超 20 行函数按职责拆分（长期任务创建/query_tasks/service_api/结果卡片） |
| FR-5 | Info Tab 新增 FontManager 只读演示与 i18n 门面演示分组 |
| FR-6 | InfoTab 主题信号经 QObject 守卫连接，控件销毁自动断开 |
| FR-7 | Task Tab 演示 stop(delete_from_storage=False) 与 is_long_task_running 判定 |
| FR-8 | LLM Tab 演示工具流式对话、会话流式带图（images）、模型能力标签 |
| FR-9 | LLM 全部触发按钮请求进行中禁用，结果/错误事件到达后恢复 |
| FR-10 | 布局间距/限高收敛到 `ui/metrics.py` 常量模块；原始 JSON 弹窗改写结果面板；MCP 卸载主动断开远程连接；订阅事件加锁 |

## 4. 非目标（明确不动项）

- 不变更插件版本号；
- 不改 `information.py` 的 service_api 类型写法（`"str"`/`"any"` 是框架文档惯例，列为跟进项）；
- 结果卡片 HTML 模板内的样式字面量（margin/border-left 等）不常量化；
- test 分支测试代码不在本插件仓库维护，本任务不改测试；
- 真实 Provider 端到端联调不在本任务范围（无实配 Provider，仅离线验证代码路径）。

## 5. 验收标准

- 8 处 `register_sync_task` 调用点全部消除（Grep 无残留）；
- 布局魔法数（间距/限高）全部替换为 metrics 常量（0 值豁免）；
- `scripts/check_i18n_completeness.py --plugin-root plugin` 校验通过；
- 各功能点离线冒烟脚本断言全过（temp/ 下验证脚本）；
- 按功能颗粒度提交 commit（`<type>(framework_api_demo): <中文描述>`）。
