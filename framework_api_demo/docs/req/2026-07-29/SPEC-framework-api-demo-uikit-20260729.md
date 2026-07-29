# SPEC：framework_api_demo UI 拆分与迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 技术方案与设计决策（Why）

| 决策 | 理由 |
|---|---|
| UI 拆分为 `ui/main_widget.py` 的 `MainWidget`，`entrance.py` 仅留胶水层 | entrance.py 原 802 行 UI/逻辑混杂；拆分后插件入口只负责生命周期、服务初始化与控件创建，与 color_converter 等已迁移插件结构一致 |
| `MainWidget` 构造函数注入 5 个演示 Service | UI 层不自行创建/获取服务，保持「ui/ 不写业务逻辑」约束；处理器仍按原名 `self.data_service` 等引用，纯移动 |
| 整体删除插件 QSS（`style/main.qss`）与 `_load_plugin_style` 样板 | 旧 QSS 依赖已删除的 `utils.style_qss.QssRegistry`；UIKit 组件默认样式 + 全局 `build_qss` 覆盖全部控件并自动跟随亮/暗主题 |
| `QTabWidget` → `Tabs` | `Tabs` 是 `QTabWidget` 子类，`addTab` 语义完全一致，默认 `line` 变体直接复用全局 QSS |
| 结果/日志区 `TextArea` 设置 `QFont(MONO_FAMILY)` | 替代原 QSS 的等宽字体声明，JSON/日志对齐展示；与 background_task_demo 等插件做法一致 |
| `_display_result` 颜色取 `T("color.danger")`/`T("color.success")` 当前值 | 令牌随主题取色。**已知限制**：HTML 卡片在每次调用时构造，只取调用时刻的令牌值；历史卡片不随主题切换重渲染（重渲染需缓存全部结果数据，复杂度收益不成比例），新产生的卡片始终使用当前主题色 |
| `QMessageBox`×5 → `Message.info/warning(self, ...)` | QMessageBox 为模态弹窗且不走 UIKit 主题；Message 为顶部轻提示，行为对齐框架反馈体系。结果主体仍走 `_display_result` 面板，弹出的只是原始结果摘要，与原行为一致 |
| `SignalBridge` 保留在 entrance.py | 插件加载早期（控件未创建）日志经信号桥转发；`_on_log_message` 槽在控件存在时转发给 `MainWidget.append_log`，未创建时丢弃（与原行为一致） |
| 版本号 release.1.0.0 → release.1.1.0 | UI 重构 + 框架 API 适配属功能层面改进，升级小版本 |

## 2. 拆分结构

```mermaid
flowchart TD
    subgraph entrance.py（胶水层）
        P[FrameworkAPIDemoPlugin<br/>plugin_name / on_plugin_loaded<br/>_get_data_provider / _register_with_provider<br/>_init_services / _create_widget]
        SB[SignalBridge<br/>log_message]
    end
    subgraph ui/main_widget.py（UI 层）
        MW[MainWidget<br/>布局构建 _build_* / _create_*<br/>事件处理 _on_*<br/>_display_result / append_log]
    end
    subgraph function/services/core_service.py（服务层，不变）
        SVC[DataDemoService / TaskDemoService<br/>LLMDemoService / APIDemoService<br/>FrameworkInfoService]
    end
    P -->|_create_widget 注入 5 个 Service| MW
    SB -->|加载早期日志| P
    P -->|_on_log_message 转发| MW
    MW -->|调用| SVC
    MW -->|T 令牌 / MONO_FAMILY| TM[ThemeManager 全局主题]
```

- `entrance.py`（107 行）：`SignalBridge` + `FrameworkAPIDemoPlugin` 胶水层；
- `ui/main_widget.py`（856 行）：`MainWidget`，承载全部 UI 构建与事件处理；
- `function/services/core_service.py`：服务层未改动（get_models 消费点原本即
  Dict 语义，见 §4）。

## 3. 控件映射

| 原控件 | 新控件 |
|---|---|
| `QPushButton` + `setProperty("class", "primary")` | `Button(text, variant="primary")` |
| `QPushButton`（含 "subtle" 的「清除结果」） | `Button(text)`（默认变体） |
| `QComboBox` + `addItems` | `ComboBox(items=[...])` |
| `QLineEdit("默认值")` + `setPlaceholderText` | `LineEdit(text=..., placeholder=...)` |
| `QSpinBox`（5~3600，默认 60，后缀" 秒"） | `SpinBox(minimum=5, maximum=3600, value=60)` + `setSuffix(" 秒")` |
| `QListWidget` | `ListWidget()`（保留 `setMaximumHeight`） |
| `QTextEdit`（结果/日志，只读等宽） | `TextArea()` + `setReadOnly(True)` + `setFont(QFont(MONO_FAMILY))` |
| `QTextEdit`（聊天/调用结果、Info 区） | `TextArea()` + `setReadOnly(True)` |
| `QTabWidget` | `Tabs()`（默认 `line` 变体） |
| `QMessageBox.information` ×4 | `Message.info(self, text)` |
| `QMessageBox.warning` ×1 | `Message.warning(self, text)` |
| `_display_result` 内 `#EF4444` / `#10B981` | `T("color.danger")` / `T("color.success")` |

保留原生 Qt：`QGroupBox`、`QFormLayout`/`QVBoxLayout`/`QHBoxLayout`、
`QScrollArea`（Tab 内容滚动容器，样式由全局 QSS 提供）。

## 4. get_models 返回类型适配说明

框架 `LLMProvider.get_models(provider)`（core/llm/llm_provider.py:1117）返回
`Dict[str, List[ModelInfo]]`，键为提供商实例 id。消费点核查结果：

- `function/services/core_service.py`：
  - `LLMDemoService._get_all_models()`（无参路径）：按 `models_dict.items()`
    遍历 Dict 并把每个 `ModelInfo` 转为 `{"id", "name"}` 字典——**已是 Dict
    语义，无需改动**；
  - `LLMDemoService._get_models_by_provider()`：走
    `get_cached_models(provider)`，返回 `List[ModelInfo]` 未变——无需改动；
- `ui/main_widget.py` 的 `_on_get_models()`：`isinstance(models, dict)` 分支
  按 `{实例id: [模型...]}` 双层遍历展示 `实例id: 模型名`，与 Dict 语义一致；
  保留 list 兜底分支兼容服务层按 provider 查询的返回形态。

即本次适配为**确认兼容 + 注释标明 Dict 语义**，无语义改动；另以
`temp/smoke_framework_api_demo.py` 用 Dict 假数据（monkeypatch）验证服务层与
UI 层消费路径均不抛错。

## 5. 涉及修改的文件

- `entrance.py`：重写为胶水层（删除全部 UI 代码、`utils.style_qss` 导入、
  `get_widget` 主题缓存覆写、`_load_plugin_style`、未使用的 `uuid`/`get_name`
  导入）；
- `ui/main_widget.py`：新建，承载全部 UI 构建与事件处理（UIKit 组件）；
- `ui/__init__.py`：更新包 docstring；
- `information.py` / `IXPlugin.json`：version → `release.1.1.0`；
  IXPlugin.json description 核对无乱码，重写为简洁中文；
- `service.py`：docstring 经字节级核对为正常 UTF-8 中文，无乱码，未改动；
- 删除：`style/` 目录、全部 `__pycache__`。

## 6. 验证

- `temp/verify_batch1.py framework_api_demo`：插件导入、实例化、双主题重建
  PASS；
- `temp/smoke_framework_api_demo.py`：monkeypatch `get_models` 返回 Dict 假
  数据，验证 `LLMDemoService.get_models()`（无参/指定 provider 两条路径）与
  `MainWidget._on_get_models()` 不抛错，PASS。
