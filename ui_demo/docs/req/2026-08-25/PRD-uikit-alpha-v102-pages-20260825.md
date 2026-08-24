# PRD：ui_demo 补齐 UIKit alpha-v1.0.2 新能力演示页

- 创建日期：2026-08-25
- 修改日期：2026-08-25

## 概述

InstructionX_UIKit 于 alpha-v1.0.2 引入两项重要新能力：**MarkdownView 组件的
LaTeX 公式 / Mermaid 图表渲染与流式追加**，以及**第 13 个布局预设
chat_conversation（流式对话布局）**。ui_demo 作为「UIKit 组件橱窗」插件，
当前仍停留在 57 组件 / 12 布局的旧口径，缺少上述能力的演示页，开发者无法
通过插件直观学习新 API 的用法。

本需求为 ui_demo 补齐这些演示页，并同步全部元数据（导航注册表、组件目录、
IXPlugin.json / information.py 描述、语言包）。

## 用户故事

- 作为插件开发者，我希望在 ui_demo 中看到 MarkdownView 的完整渲染能力
  （标题 / 列表 / 代码块 / 表格、LaTeX 公式、Mermaid 围栏、流式追加），
  并附有最小用法示例，以便在自己的插件中正确使用。
- 作为插件开发者，我希望看到 chat_conversation 流式对话布局的实尺寸演示，
  包括用户 / AI 气泡、气泡操作条（复制 / 删除 / 编辑 / 重新生成 / 继续生成）、
  AI 气泡自定义 info 文案与 `set_message_stats` 统计展示。
- 作为开发者，我希望在蓝图演示页直接看到当前视口的渲染后端
  （GL / 软件），便于确认环境是否启用 GPU 加速。

## 功能需求

1. **F1 MarkdownView 演示页**（组件 · 展示分类，导航键 `markdown_view`）：
   - 基础渲染分区（标题 / 行内样式 / 列表 / 引用 / 代码块 / 表格 / 链接）；
   - LaTeX 公式分区（行内 / 块级公式）；
   - Mermaid 围栏分区（flowchart / sequenceDiagram / pie），附交互查看器
     说明文案；
   - MermaidView 独立使用小节（脱离 MarkdownView 的交互查看器）；
   - 流式 `append_markdown` 追加演示分区（自动播放 + 重新播放按钮）；
   - 空状态分区；
   - 页面顶部「用法」代码标签。
2. **F2 chat_conversation 布局演示页**（布局预设分类，导航键
   `chat_conversation`，成为第 13 个布局）：
   - 初始示例对话（用户 / AI 气泡，AI 气泡带 `info` 自定义文案，内容覆盖
     Markdown / 公式 / Mermaid）；
   - 气泡操作条常显，复制 / 删除 / 编辑 / 重新生成 / 继续生成信号全部接线：
     重新生成与继续生成驱动模拟流式输出，删除 / 编辑 / 提交更新页内
     状态提示行；
   - `set_message_stats` 以真实值覆盖首条 AI 消息的统计展示；
   - 底部输入区提交后模拟 AI 逐段流式回复；
   - 页面顶部「用法」分区（布局页自带）。
3. **F3 蓝图页渲染后端状态行**：blueprint 演示页工具条下方新增一行状态
   标签，经 `InstructionX_UIKit.blueprint.viewport.gl_available()` 展示
   当前视口渲染后端（GL / 软件），文案入语言包。
4. **F4 元数据同步**：
   - `ui/pages/__init__.py` 的 `NAV` 注册新页（含 nav 语言键 zh + en）；
   - `function/component_catalog.py` 同步（组件 57 → 58、布局 12 → 13）；
   - `IXPlugin.json` 与 `information.py` 描述中的过时统计口径更新；
   - 新页面全部用户可见文案入 `text/zh.xml` + `text/en.xml`。
5. **F5 i18n 校验**：`scripts/check_i18n_completeness.py --plugin-root plugin`
   通过；源码 `tr()` 键在 zh.xml 全覆盖、zh/en 键集合一致。

## 非功能需求

- 遵循插件开发规范：函数 ≤ 20 行、嵌套 ≤ 3 层、无魔法数、import 置顶、
  中文注释 / docstring；
- offscreen 环境可冒烟：全部演示页（含新增页）创建无异常，MarkdownView 页
  `grab()` 截图非空白；Mermaid WebEngine 在 offscreen 走自绘降级路径属预期；
- 不修改框架代码与 UIKit 库文件，不改动插件版本号（保持 release.1.0.4）；
- 插件向后兼容：不变更既有 `service_api`，仅新增演示页与文案。

## 插件类型判断

既有插件 `ui-demo`（单插件，位于插件集仓库 `plugin/` 下）的功能增补，
不涉及描述文件结构变更；`IXRepo.json` 无需调整。

## 描述文件清单

| 文件 | 变更 |
|------|------|
| `plugin/ui_demo/IXPlugin.json` | description 中「57 组件、12 布局」口径更新为 58 / 13（zh + en） |
| `plugin/ui_demo/information.py` | description 属性同步更新 |
| `plugin/ui_demo/text/zh.xml` / `text/en.xml` | 新增 nav / markdown_view / layouts / layout_samples / blueprint 键 |
| `plugin/IXRepo.json` | 不变 |
