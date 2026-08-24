# SPEC — Blueprint OpenCV P1/P2 优化批次

> - 创建日期：2026-08-24
> - 修改日期：2026-08-24
> - 插件 id：`blueprint-opencv` / 目录：`plugin/blueprint_opencv/`
> - 关联文档：`docs/req/2026-07-30/SPEC-blueprint-opencv-20260730.md`（初版，本次含修订注记）、`SPEC-shared-pipeline-runtime-20260824.md`（同目录，共享运行实例前置批次）

## 1. 背景与目标

初版落地后遗留若干「声明未接线 / 实现与文档脱节 / 小型缺陷」问题。本批按
P1（资产补齐、配置接线、文档元数据同步）与 P2（缺陷修复与代码质量）两级
处理，全部为既有行为的小型修正，不引入新功能、不改变 service_api 契约。

## 2. 技术决策（Why）

### 2.1 预置示例图资产（P1）

- `assets/preset_graph.json` 由临时脚本经真实 `MainWidget.build_preset_graph()`
  等价路径生成（`canvas.to_dict()` 落盘），保证与运行时构建逻辑一致；
- **可移植性决策**：落盘前把 load_image 节点的 `file_path` 改写为相对插件
  目录路径（`assets/sample.png`），service 层 `_read_preset_graph` 读出后
  统一解析为绝对路径——避免资产绑定开发机绝对路径；
- 干净图自检：`graph_migration.migrate_graph_dict` 无改动 + 节点类型全部
  在 `NODE_DEFINITIONS` / 内置 start 内。

### 2.2 配置接线（P1）

新增 `ui/plugin_config.py` 作为 config/default.json 的唯一读取入口
（缺失/损坏记 WARNING 回退缺省），消费方接线如下：

| 配置键 | 消费方 | 说明 |
|--------|--------|------|
| `preview.max_width/max_height` | `ui/preview_panel._scaled` | 替换原硬编码常量 |
| `panel.right_panel_width` | `ui/main_widget._build_right_panel` | 原模块级读取迁入 plugin_config |
| `panel.min_canvas_width` | `ui/main_widget._build_layout` | 画布 `setMinimumWidth` |
| `graph.max_nodes` | `ui/main_widget.__init__` → `service.set_max_nodes` → `PipelineController.set_max_nodes`（锁保护） | service/function 层不读配置，`DEFAULT_MAX_NODES` 常量保留为跨插件路径缺省 |
| `assets.sample_image` | `ui/main_widget.build_preset_graph` | 相对路径按插件根目录解析 |

**删除项决策**：`assets.preset_graph` 从配置删除——其唯一消费方是 service
层（跨插件 / MCP 路径不读配置文件），`PRESET_GRAPH_RELATIVE_PATH` 常量为
单一来源，配置中的重复声明只会造成双来源失真。

### 2.3 exec 链判环三色标记（P2 缺陷修复）

原实现为「visited 出栈检查」的迭代 DFS：节点一旦入 visited，再次到达即
报环。菱形汇聚（start→A→C、start→B→C，C 从两条路径到达）被误报为环。
改为三色标记 DFS：灰 = 当前 DFS 路径上（重复到达成环，抛
`NodeExecutionError("exec 链存在环路，无法运行")`，错误语义不变）；
黑 = 已完成（重复到达属正常汇聚，跳过）。执行序列保持先序 DFS 顺序。

### 2.4 其他 P2 决策

- **死代码**：`image_codec.decode_png` / `normalize_size` /
  `node_catalog.registration_payloads` / `_to_payload` 无任何调用方
  （含 test 分支测试，已 grep 确认），删除并同步模块 docstring；
- **存档读取噪音**：`_read_saved_graph` 先校验图名（拒绝路径穿越字符，
  替代原 `get_asset_path` 读侧消毒）再 `is_file()` 预检——不存在属正常
  回退路径（首次启动 / 未保存），静默返回 None；仅损坏记 WARNING；
- **语言切换刷新体区**：`_retranslate_ui` 末尾追加 `_refresh_node_bodies()`
  （借 `node.changed` 触发体区标签按新语言重取词，体区构建时捕获的 i18n
  门面在调用时解析当前语言）；
- **当前存档名同步**：`GraphListPanel` 新增 `graph_renamed(str,str)` /
  `graph_deleted(str)` 信号，重命名 / 删除当前已加载存档后 MainWidget
  同步 `_current_graph_name`（跟随新名 / 置空），避免后续「保存」以旧名
  重建存档；
- **槽函数瘦身**：`_on_run_finished` / `_load_graph_by_name` / `_persist_graph`
  / `_prompt_rename` / `_confirm_delete` 拆分为「≤5 行槽 + 视图编排辅助
  方法」，行为不变；状态字面量 `"running"/"done"/"error"` 改用
  `function/constants.py` 的 `NODE_STATUS_*` / `RUN_STATUS_*` 常量；
- **工具条运行态**：新增显式 `self._running` 字段（`set_running` 维护），
  不再用「停止按钮是否禁用」反推运行态；
- **对话框统一**：新增 `ui/dialogs.py`（`prompt_text` / `confirm` / `warn`，
  阻塞式 UIKit `Dialog`），替换全部 `QInputDialog` / `QMessageBox`；
  `QFileDialog` 为系统级对话框、UIKit 无对应组件，保留并注释说明；
- **覆盖确认枚举复用**：`_confirm_overwrite` 复用 `GraphListPanel.existing_names()`
  （面板每次增删改名后自刷，与磁盘一致），不再重复调 `list_graphs`；
- **i18n 残留**：` · ` 分隔符、`ms` 单位与固定宽空格为跨语言通用符号 /
  版式间隔，刻意不入语言包，加注释说明。

## 3. 元数据同步

- `IXPlugin.json` homepage → 插件集仓库
  `https://github.com/KKPIP-Tech/instructionx-debug-plugin-cluster`；
- `information.py` developer 与 author 统一为 `InstructionX Team`；
- `skill_description` 硬编码中文属框架限制（IPluginInfo 无 i18n 机制），
  保留并加注释说明。

## 4. 验证

- `temp/bp_preset_graph_smoke.py`：无存档回退预置图、相对路径解析为存在的
  绝对路径、预置图实际运行 done、preview PNG 可解码——全部通过；
- `temp/bp_cycle_detect_smoke.py`：线性链顺序、真环 a→b→a 抛「环路」、
  菱形汇聚不误报且汇聚节点仅一次、扇出保持先序——全部通过；
- `temp/bp_shared_runtime_smoke.py`（前置批次）：回归通过；
- 多个内联 offscreen 检查：MainWidget 构建、set_max_nodes 透传、
  画布最小宽、existing_names、运行汇总文案分支、toolbar 运行态字段、
  `_retranslate_ui` 体区刷新——全部通过；
- 已知待办（test 分支）：`test_service.py::test_load_missing_falls_back`
  断言「预置图缺失 → 空图」，本批补齐 preset_graph.json 后该断言需更新为
  「回退预置示例图（5 节点）」，在 test 分支合并本批改动时同步修订。

## 5. Commit 颗粒度

本批按功能拆分为 10 个 commit（preset 资产 / 存档读取静默 / 判环三色 /
死代码清理 / 配置接线 / 对话框统一 / 存档名同步 / 槽函数瘦身 / 工具条
运行态 / 语言体区刷新 / 文档同步），详见 `git log`。
