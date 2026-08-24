# SPEC — framework_api_demo 健壮性与新 API 覆盖优化技术方案（P0/P1/P2 批次）

- 创建日期：2026-08-24
- 修改日期：2026-08-25
- 对应 PRD：`PRD-hardening-framework_api_demo-20260824.md`

## 1. 关键设计决策（Why）

### D1 P0-1：`register_sync_task` → `register_async_task`（8 处）

框架 `BackgroundTaskManager.register_sync_task` 在**调用线程内联执行**——
UI 线程调用即阻塞 UI。演示插件中 LLM 对话/嵌入/工具调用、MCP 连接/断开、
线程工具演示均为阻塞型操作，必须经 `register_async_task` 提交线程池。

- 服务层统一经辅助方法提交（`llm_service._submit_async_task`、
  `mcp_service._submit_mcp_task`），集中处理：管理器已关闭时
  `register_async_task` 返回 `None`，统一返回 `err.manager_closed` 错误字典；
- 任务回调在工作线程执行，一律经 notifier + `run_in_ui_thread` 封送回 UI。

### D2 P0-2：chat/embed 后台任务化 + 事件协议上抛

`send_chat`/`send_embedding` 原是 UI 线程同步 HTTP。改造为：

- 服务层：发起即提交后台任务并返回 `{"success": True, "task_id": ...}`；
  完成/失败经 notifier 发送协议事件（`CHAT_DONE_EVENT` /
  `CHAT_ERROR_PREFIX + error` / `EMBED_*`），聚合结果存
  `_last_chat_result`/`_last_embed_result` 供 UI 拉取；
- UI 层：`_dispatch_chat_result_event` 按协议分发，成功拉取
  `get_last_chat_result()` 展示，失败写错误前缀到聊天区；
- 顺带删除 `_on_send_embed` 中 `Message.info(str(result))` 裸 dict 弹窗。

### D3 P1-6：主题信号守卫方案选型

需求：InfoTab（非 QObject）监听单例 `ThemeManager.theme_changed`，
热重载销毁控件树后必须自动断开。

- **废弃方案**：`scroll.destroyed.connect(显式 disconnect)`——offscreen/
  延迟销毁路径下 `deleteLater` 不保证触发 `destroyed`，验证失败；
- **采纳方案**：`_ThemeConnectionGuard(QObject)` 作为滚动容器的**子对象**
  充当信号接收者，控件销毁时 Qt 自动断开其全部接收方连接；守卫经
  `weakref.WeakMethod` 转发给 Tab 回调，Tab 已回收时跳过。
  已验证：销毁后访问守卫报 "already deleted"，残留连接消除。

### D4 P2-10：LLM 触发按钮防重入

- `LLMTab._begin_llm_request(btn)`/`_end_llm_request(btn)` 仅做
  `setEnabled(False/True)`；
- 发起处 disable，发起即失败立即恢复；后台请求的 DONE/ERROR 事件分发处恢复；
- 会话流式两个入口（普通/带图）共用 STREAM_DONE/STREAM_ERROR 事件，
  事件到达时两个按钮一并恢复（`setEnabled(True)` 幂等无害）；
- 覆盖 10 个按钮：chat/chat_stream/conv_send/conv_stream/conv_stream_img/
  tool_chat/tool_stream/embed/image_gen/tts。

### D5 其他杂项决策

- **布局度量**：新建 `ui/metrics.py` 集中间距/边距/限高常量（像素），
  0（无边距/无间距）属无语义字面量豁免；
- **原始 JSON 展示**：Function Tools JSON 由 `Message.info` 截断弹窗改为
  写入结果面板（新增 i18n 键 `tab_api/title.tools_json`），删除
  `_TOOL_JSON_DISPLAY_LEN`；data_tab 两处注册结果 `Message.info(str(result))`
  删除（结果已进结果面板）；
- **MCP 卸载清理**：`MCPDemoService.cleanup()` 遍历
  `mcp_client.list_connected_servers()` 逐个 disconnect，逐项容错记日志；
  entrance `_iter_cleanup_services` 纳入 mcp_service；
- **订阅事件线程安全**：data_service 增 `_events_lock`，事件 append/截断与
  读取加锁（订阅回调在工作线程、查看在 UI 线程）；
- **配置加载**：`_load_config` 失败记 WARNING；按文件 mtime 模块级缓存
  （签名不变，test 分支引用它）。

## 2. 提交清单（plugin 仓库 dev 分支）

| commit | 主题 |
|--------|------|
| d0838b0 | fix：8 处 register_sync_task → register_async_task |
| 7924a16 | fix：chat/embed 后台任务化 + notifier 事件上抛 |
| 09d3186 | fix：_load_config 补 WARNING 日志 + mtime 缓存 |
| e1a4c5e | refactor：拆分超 20 行函数 + import 顺序修正 |
| 05dae83 | feat：Info Tab FontManager 只读 + i18n 门面演示 |
| 4290c7d | fix：InfoTab 主题信号经 QObject 守卫连接 |
| 3cfb05d | feat：stop(delete_from_storage=) 与 is_long_task_running 演示 |
| 9760229 | feat：工具流式 / 会话流式带图 / capability_label 演示 |
| 960820e | refactor：布局度量 metrics 常量化 + import 排序 + 事件加锁 |
| 825e79c | fix：LLM 按钮防重入 + JSON 弹窗改结果面板 + MCP 卸载断开 |

## 3. 验证记录

- `temp/fad_p0_thread_check.py`：async 线程池 / sync 内联对照、线程封送探针，全过；
- `temp/fad_p02_chat_embed_check.py`：chat/embed 事件协议与结果拉取，全过；
- `temp/fad_p210_misc_check.py`：六 Tab offscreen 构建、10 按钮防重入状态迁移、
  MCP cleanup 容错、事件锁存在性，16 项全过；
- `scripts/check_i18n_completeness.py --plugin-root plugin`：zh/en 校验通过；
- 行为冒烟（stop 保留记录 / 运行中判定 / 错误文案）全过。

## 4. 已知限制与跟进项

- P2-9 真实 Provider 端到端只能离线验证代码路径（无实配 Provider 环境）；
- offscreen 平台下 QFontDatabase 无字体，`resolve_family` 回退为空字符串属
  平台差异，真实 GUI 下正常；
- `information.py` service_api 的 `"str"`/`"any"` 类型写法为框架文档惯例，
  本任务不动，建议框架侧统一后再跟进；
- test 分支受影响的语义仅 `stop_long_task` 错误文案（保留"不存在"字样，
  既有断言兼容）与 send_chat/send_embedding 同步变异步（test 分支无
  llm_service 测试文件）。
