# SPEC：ui_demo 缺陷修复与 P1 级加固（hardening）

- 创建日期：2026-08-25
- 修改日期：2026-08-25

对应需求：ui_demo 插件 P0/P1 缺陷修复清单（不含存量超长函数拆分，
该项由后续任务单独处理）。本 SPEC 记录各项修复的技术方案、设计决策
与验证记录。

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
