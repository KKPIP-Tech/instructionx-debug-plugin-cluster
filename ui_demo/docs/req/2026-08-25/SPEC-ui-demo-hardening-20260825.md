# SPEC：ui_demo 缺陷修复与 P1 级加固（hardening）

- 创建日期：2026-08-25
- 修改日期：2026-08-25（追加 P2 超长函数拆分批次）

对应需求：ui_demo 插件 P0/P1 缺陷修复清单与存量超长函数拆分。
本 SPEC 记录各项修复的技术方案、设计决策与验证记录。

## 范围与边界

- 仅修改 `plugin/ui_demo/` 内文件；临时验证脚本放框架根 `temp/`（不提交）。
- 不触碰框架代码与 UIKit 库；版本号保持 `release.1.0.4` 不变。
- 不回退上一批次的口径（58 组件 / 13 布局、蓝图后端状态行等）。

## 修复项与设计决策

### P0-1 主题切换悬挂回调

**问题**：`ThemeManager` 为全局单例，多处把 `theme_changed` 直接 connect
到捕获 self / 控件强引用的 lambda 且不 disconnect；页面缓存清空
（语言切换重建）或热重载后，回调访问已删除的 C++ 对象抛 RuntimeError。

**方案**：`ui/pages/common.py` 新增统一 helper `connect_theme_refresh(widget,
callback=None)`——weakref 持有目标控件，回调发现目标被回收或其 C++ 侧
已销毁（RuntimeError）时主动 `disconnect`；`callback` 签名统一为
`callback(widget)`，缺省 `QWidget.update`。沿用 `anim_painted.py`
`_rebuild_cards_on_theme` 的既有正确模式。

替换点（5 处）：`tokens.py` 的 `_Bar` / `_RadiusBox`、
`anim_property.py` 的 `_gflow_card` / `_morph_stage`、
`layout_samples.py` 的 `_DemoBarChart`、`common.py` 的 `ColorBlock`。
`_morph_stage` 的闭包 `_style` 提升为模块级 `_morph_style(widget, radius)`，
回调只捕获 `state` 字典、不再强引用控件。全插件 grep 确认无遗漏
（markdown_view / blueprint / main_widget 无 theme_changed 连接）。

### P0-2 蓝图页运行/单步互斥

**问题**：`step_once()` 在「运行」进行中点击时不停 `self._timer`，
QTimer 回调 `_complete_node` 与单步交错推进 `_idx`，节点状态 /
耗时徽标错乱。

**方案**：引入显式状态枚举 `_RunState`（`IDLE / RUNNING / STEPPING`）
替代原 `_mode` 字符串；`_set_state()` 统一切换并联动工具条
（RUNNING 期间「单步」按钮置灰）。`step_once` 在 RUNNING 时直接忽略；
`run_all` 随时可重新开始（原语义保留）；完成 / 重置统一回 IDLE。
演示语义不变：单步立即完成节点、运行按随机耗时逐节点推进。

### P1-3 模块级弹出层列表无限增长

**问题**：`display._POPOVERS` / `feedback._KEEP` 为模块级全局列表，
每次点击 append 且从不清理，且违反「禁模块级全局变量持有状态」。

**方案**：删除两个模块级列表，改为各演示页的 `_keep_popups` 实例属性
持有（Popover 构造期单个；Drawer / Tour 按点击次数增长），随页面控件
生命周期释放。演示功能不变。

### P1-4 静默吞异常补日志

`common.DemoCard._safe_play`、`playground._stop_handle` / `ParamCard.replay`
（两处）、`pages/__init__._with_usage`（AttributeError/TypeError）原静默
pass，统一改为经 `utils.logging_tools.LoggerManager` 记 DEBUG 日志
（含上下文），保持「演示不中断」的意图不变。LoggerManager 为框架单例，
模块级 `_logger = LoggerManager()` 的写法跟随 blueprint_opencv 既有先例。

### P1-5 魔法数与漂移

- `blueprint.py` 标题 `setPixelSize(18)` → 复用 `common.title_label()`
  （原 `_title_label` 提升为公开 API 并入 `__all__`），字号走
  `font.title.lg=20` 令牌，与其他页一致；
- `main_widget.py` 内容区宽 `1040` → `config/default.json` 新增
  `ui.content_default_width`（`_DEFAULT_UI_CONFIG` 同步兜底）；
- `playground.py` 面板默认宽 `280` → 命名常量 `DEFAULT_PANEL_WIDTH`
  （配置装载在 main_widget，playground 反向引用会循环依赖，故用常量）；
- `playground.add_specs` 缓动清单硬编码 → `list(tk.EASING)` 动态读取，
  与 `tokens.py` 动效区同源。

### P1-6 setProperty 一致性

`layout_samples.py` 12 处 `setProperty("role", ...)` 全部改为 UIKit
`set_property()`（内部触发 unpolish/polish），与插件其余页面一致。

### P1-7 offscreen 降级写框架根目录

`blueprint.py` `_json_path` 的 offscreen 降级原写 `cwd/blueprint_demo.json`
（框架根），改为 `cwd/temp/blueprint_demo.json`（目录不存在则创建），
注释说明仅 offscreen 测试路径触发；新增命名常量 `_OFFSCREEN_FALLBACK_DIR`。

### P1-8/9/10 元数据与插件名口径

- `developer_email`：`IPluginInfo` 契约为**抽象 property**，不能删除字段；
  占位假邮箱 `support@example.com` 改为插件仓库内其他官方插件
  （blueprint_opencv / framework_api_demo）实际使用的统一邮箱
  `support@instructionx.dev`；
- `developer` 与 `IXPlugin.json` author 统一为 `InstructionX Team`
  （blueprint_opencv 已有「两者保持一致」的注释惯例）；
- `developer_website` 与新增 `IXPlugin.json` homepage 均为
  `https://github.com/KKPIP-Tech/instructionx-debug-plugin-cluster`；
- `IXPlugin.json` name 的 zh/en 同值字典退化为纯字符串 `"UI Demo"`
  （description 双语有实际差异，保留字典形式）；
- `entrance.plugin_name` **保持 `"UI\nDemo"` 不变**：经查框架技能面板
  （`ui/skills_panel/panel.py:204`）显示名取 `IPlugin.plugin_name` 属性
  而非 IXPlugin.json name，SkillButton 为双行排版，`\n` 形式与
  blueprint_opencv（`"Blueprint\nOpenCV"`）等官方插件一致；已加注释说明。

## 验证记录

全部验证在 `QT_QPA_PLATFORM=offscreen` +
`QT_QPA_FONTDIR=C:\Windows\Fonts` 下完成（临时脚本在框架根 `temp/`）：

| 验证 | 脚本 / 命令 | 结果 |
|------|------------|------|
| 77 页创建 + 销毁后主题切换无 RuntimeError | `temp/ui_demo_theme_safety_smoke.py` | 通过 |
| 蓝图页运行/单步互斥、完成回 IDLE、reset 中断 | `temp/ui_demo_blueprint_mutex_smoke.py` | 通过 |
| _POPOVERS/_KEEP 已移除，弹出层随页面持有 | 内联 offscreen 断言 | 通过 |
| 吞异常路径记 DEBUG 且不抛出 | 内联 offscreen 断言 | 通过 |
| 标题字号=令牌 20 / easings=tk.EASING / 面板宽常量 / config 宽度 | 内联 offscreen 断言 | 通过 |
| offscreen 降级写 temp/ 且不写框架根 | 内联 offscreen 断言 | 通过 |
| 元数据 / IXPlugin.json / plugin_name 一致性 | 内联断言 | 通过 |
| 全量回归（NAV 77 页 + markdown/chat/蓝图冒烟）zh + en | `temp/smoke_ui_demo_v102_pages.py`（SMOKE_LANG=zh/en） | 通过 |
| i18n 完整性校验 | `scripts/check_i18n_completeness.py --plugin-root plugin` | 通过 |

## 对 test 分支的影响（跟进事项）

- `test/ui_demo/test_pages_smoke.py` 的 `TestBlueprintRunSimulation`
  （step 推进 / run 完成 / reset）语义不变，预期不受影响；JSON round-trip
  测试 monkeypatch `_json_path`，不受 P1-7 影响。未在本地 test 分支运行。
- `test/ui_demo/test_information.py` 中 `test_required_text_fields_non_empty`
  断言 developer_email 非空——本次取真实邮箱值而非置空，该测试不受影响。
- 该文件另有 `test_version` 仍断言 `release.1.0.3`（上一批次升 1.0.4 时
  未同步），属既有失配，需由测试分支维护方更新，不在本次范围。

## P2 存量超长函数系统性拆分（纯重构）

### 目标与口径

- 硬性限制：单个函数 / 方法正文 ≤ 20 行（剔除 docstring / 注释 / 空行，
  AST 扫描脚本 `temp/scan_ui_demo_long_functions.py`，嵌套 def 行数计入
  外层函数）。
- 拆分前基线扫描共 **28 处**超 20 行，拆分后复扫为 **0 处，无豁免项**。
- 纯重构：控件树结构、属性、信号连接、取词键、绘制输出全部保持等价。

### 拆分清单

| 文件：函数（原行数） | 拆法 |
|------|------|
| feedback.create_steps_page（85） | 状态与游乐场闭包下沉为 `_StepsDemo` 类；参数注册按 结构 / 节点 / 连接线 / 可点击 拆小方法；默认状态与状态选项提取为 `_steps_default_state` / `_steps_status_options` |
| feedback.StepsEx._paint_horizontal（28）/ _paint_vertical（24） | 单步绘制提取 `_paint_step_horizontal` / `_paint_step_vertical`，连接线提取 `_draw_link` |
| feedback.StepsEx._draw_node（36） | 按状态字形拆 `_draw_finish_glyph` / `_draw_error_glyph` / `_draw_index_glyph` |
| feedback.create_anchor_page（29） | 滚动内容区构建提取 `_anchor_scroll_content` |
| display.TimelineEx.paintEvent（58） | 按绘制阶段拆 `_paint_items` / `_paint_dot` / `_paint_item_text` / `_paint_pending`，共享上下文提取 `_TimelinePaintContext` |
| display.create_timeline_page（71） | 状态与游乐场闭包下沉为 `_TimelineDemo` 类，参数注册按 颜色 / pending / 连接线 / 布局 / 字号 拆小方法 |
| playground.add_specs（39） | if-elif 长链改 `_SPEC_HANDLERS` 查表分发，每类规格一个处理函数 |
| playground.ParamForm.add_int（28） | 控件构建 / 双向联动接线拆 `_build_int_controls` / `_wire_int_controls` |
| playground.PlaygroundPanel.__init__（23） | 标题 / 表单区 / 重置按钮行拆构建段方法 |
| playground.ParamCard.__init__（38） | 标题 / 提示 / 演示区 / 表单 / 播放按钮行拆构建段方法 |
| blueprint.exec_order（32） | 拆 `_collect_exec_edges` / `_topo_sort` / `_kahn_order` |
| blueprint.BlueprintDemoPage.__init__（34） | 运行状态 / 图画布 / 根布局 / 定时器信号拆 4 个初始化段方法 |
| blueprint._build_preset（21） | 节点创建 / exec 链 / 数据引脚拆 3 个小方法 |
| charts.ChartDemoCard.__init__（31） | 标题 / 图表 / 参数表单拆构建段方法 |
| charts._build_bar（22）/ _build_line（23）/ _build_grid_mix（23） | 系列构建提取 `_bar_series` / `_line_series` / `_grid_mix_series` |
| charts._build_candlestick（22）/ _build_heatmap_grid（21） | 确定性数据生成提取 `_candlestick_data` / `_heatmap_data` |
| charts._build_comprehensive（23） | 基础 option 提取 `_comp_base_option` |
| charts._comprehensive_section（28） | 大图卡 / 右侧栏构建提取 `_comp_card` / `_comp_side` |
| common.DemoCard.__init__（27） | 标题 / 演示区容器 / 播放按钮行拆构建段方法 |
| anim_painted._rcard（22） | 播放与重建闭包提取 `_make_play_fn` / `_make_rebuild_fn` |
| inputs.create_button_page（24） | 变体 / 尺寸 / 形状三分区各拆一个构建函数 |
| basic_widgets._window_parts_section（21）/ _dialogs_section（21） | 菜单栏 / 工具栏 / 对话框触发表拆独立函数 |
| tokens._spacing_radius_section（21） | spacing 行 / radius 行拆 `_spacing_rows` / `_radius_row` |

### 设计决策

- **闭包游乐场下沉为状态类**：steps / timeline 两页原以 `nonlocal` 闭包
  组织重建逻辑，拆小方法会让外层函数行数仍超限（嵌套 def 计入），故
  统一引入 `_StepsDemo` / `_TimelineDemo` 内部类持有状态与实例，回调经
  属性读写当前实例，语义与原闭包完全一致。
- **StepsEx / TimelineEx 漂移风险**：两类的参数化绘制复制了 UIKit 基类
  整段绘制实现以暴露绘制参数（基类无 setter）；本次不推动上游改 setter，
  已在两个类的 docstring 加「漂移风险提示」小节，UIKit 升级改基类绘制
  实现时需人工同步。
- **component_catalog 与 NAV 双份维护**：评估后**保持双份维护**。
  NAV 页面工厂需导入 PySide6，而 `COMPONENT_CATALOG` 被
  `function/services` 服务层在无 Qt 环境消费（纯数据约束），从 NAV 派生
  会破坏该约束；反向派生需引入「键结构 + i18n 取词」新耦合，代价大于
  60 行数据文件的同步成本。两处 docstring 已互相标注同步义务并指向本节。
- **USAGE 示例 / 蓝图引脚名固定中文**：有意决策（代码即文档），既有注释
  已齐备（`pages/__init__.py` USAGE 表、`layout_samples.py` USAGE 表、
  `blueprint.py` 节点注册注释），本次核查无需补齐。

### 验证记录（P2 批次）

| 验证 | 脚本 / 命令 | 结果 |
|------|------------|------|
| 超 20 行函数拆分前基线 28 处 → 拆分后 0 处 | `temp/scan_ui_demo_long_functions.py` | 通过 |
| NAV 全部 77 页逐页创建无异常 + markdown/chat/蓝图冒烟 | `temp/smoke_ui_demo_v102_pages.py` | 通过 |
| steps / timeline / charts / blueprint 四页 grab() 截图拆分前后逐像素对比 | `temp/ui_demo_grab_baseline.py baseline/after/compare` | 四页均 0 像素差异 |
| i18n 完整性校验 | `scripts/check_i18n_completeness.py --plugin-root plugin` | 通过 |

### 对 test 分支的影响（P2 批次）

- `git grep` 核查 `test/ui_demo/`：仅引用公开名 `NAV` /
  `BlueprintDemoPage` / `exec_order` / `preset_ids`，均保持不变；
  被拆掉的私有闭包 / 方法名（`build`、`apply_status`、`_do_play` 等）
  无任何测试引用，无需同名转发，无跟进事项。
