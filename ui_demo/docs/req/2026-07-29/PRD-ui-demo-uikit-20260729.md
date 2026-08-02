# PRD：ui_demo 插件重写为 InstructionX_UIKit 组件橱窗

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 概述

旧 ui_demo 插件基于原生 Qt 控件 + 已删除的 `utils.style_qss` 全局 QSS（`setProperty("class", ...)` 变体），在当前框架（Alpha 1.0.3）下打开界面即 ImportError，且展示效果依赖的全局样式已不存在，无修复价值。

本次将其**整体重写**为「InstructionX_UIKit 组件橱窗」：以 UIKit 独立仓库（`C:\Users\fuwa1\Documents\Project\InstructionX_UIKit`）的 `demo/` 包为基准移植演示页，使插件成为框架内浏览 UIKit 全部能力的入口，同时充当插件开发者的 UIKit 用法参考。

**核心价值**：用户（插件开发者）无需离开应用即可查阅 57 个组件、12 个布局、动画、图表、蓝图的实际效果与最小调用示例（每页顶部「用法」分区）。

## 2. 用户故事

- 作为插件开发者，我希望在应用内浏览 UIKit 每个组件的实际外观与交互，以便决定自己的插件用哪些组件；
- 作为插件开发者，我希望每个演示页顶部有一行最小调用示例（如 `Button("确定", variant="primary", size="md")`），以便直接照抄用法；
- 作为用户，我希望橱窗随框架全局亮/暗主题自动换肤，无需插件内再做主题切换。

## 3. 功能需求

- F1：左侧导航树按「分类 → 页面」两级组织，分类不可选、默认展开；右侧堆叠容器懒加载并缓存演示页；
- F2：演示内容覆盖 UIKit Demo 的 10 个分类：设计令牌、布局预设（12 页）、组件·输入（20 页）、组件·展示（18 页）、组件·反馈（19 页）、动画·属性、动画·自绘、基础控件、图表、蓝图；
- F3：每个组件页顶部展示该组件的最小调用示例（USAGE 注入机制）；
- F4：保留对外 API `get_control_list()`，返回内容更新为 UIKit 组件橱窗目录（「分类 · 名称」字符串列表）；
- F5：不提供插件内主题切换控件（全局主题由框架统一管理）；
- F6：删除旧插件全部遗留：原生控件演示页、空 `style/` 目录、style_qss 主题缓存 hack、函数级 import。

## 4. 非功能需求

- 兼容性：入口/元数据/service_api 形态符合框架 IPlugin / IPluginInfo 契约与自动注册约定（Service 类名以 Service 结尾、无参可实例化）；
- 性能：演示页懒加载，插件加载阶段不实例化任何页面；
- 可维护性：页面包（`ui/pages/`）与 UIKit 仓库 Demo 保持可比对性（仅最小必要改动），便于后续同步；
- 规范：import 全部置顶；ui/ 无业务逻辑；function/ 不依赖 PySide6；无魔法数（布局参数入 `config/default.json`）。

## 5. 插件类型判断

- 单插件（插件集成员），id `ui-demo`，目录 `plugin/ui_demo/`；
- 描述文件：`IXPlugin.json`（version 升至 `release.2.0.0`——整体重写），`IXRepo.json` 条目不变。

## 6. 描述文件清单

| 文件 | 变更 |
|---|---|
| `IXPlugin.json` | version→release.2.0.0，description 重写（原版含乱码且描述过时），keywords 增补 uikit/components |
| `information.py` | version→release.2.0.0，description/skill_description/service_api/tags 更新 |
| `IXRepo.json` | 无需变更（id/path/name 不变） |
