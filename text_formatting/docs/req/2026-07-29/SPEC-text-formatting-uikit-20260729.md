# SPEC：text_formatting UI 迁移至 InstructionX_UIKit

- **创建日期**：2026-07-29
- **修改日期**：2026-07-29

## 1. 技术方案与设计决策（Why）

| 决策 | 理由 |
|---|---|
| 整体删除插件 QSS（`style/main_widget.qss`） | 其样式硬编码且依赖已删除的 `QssRegistry.apply_variables`；UIKit 组件默认样式 + 全局 `build_qss` 已覆盖全部控件样式并自动跟随亮/暗主题 |
| 标题用 `QFont` + `T("font.lg")` 而非 QSS | 禁止硬编码字号；令牌随主题实时生效 |
| `Button(variant="primary")` 承载主操作「转换为大写/小写」 | UIKit 语义：主操作使用 primary 变体 |
| 两个转换分组收敛为 `_add_case_group(title, convert)` 单一构建方法 | 大写/小写两组结构完全一致，抽公共方法消除重复，函数 ≤20 行 |
| 版本号 release.1.0.0 → release.1.1.0 | UI 重构属功能层面改进，升级小版本 |

## 2. 控件映射

| 原控件 | 新控件 |
|---|---|
| `QLineEdit`（文本输入 ×2） | `LineEdit(placeholder="输入文本...", clearable=True)` |
| `QPushButton("转换为大写"/"转换为小写")` | `Button(..., variant="primary")` |
| `QLabel` 标题（QSS heading） | `QLabel` + `QFont(T("font.lg"), Bold)` |

## 3. 数据流向

```mermaid
flowchart LR
    UI[ui/main_widget.py<br/>LineEdit/Button] --> SVC[service.py<br/>CoreService.to_uppercase / to_lowercase]
    UI -->|T 令牌取字号| TM[ThemeManager 全局主题]
    CFG[config/default.json<br/>margins/spacing] --> UI
```

## 4. 涉及修改的文件

- `ui/main_widget.py`：UIKit 迁移（删除样式加载样板，重构为模板方法构建两组转换组件）；
- `information.py` / `IXPlugin.json`：version → `release.1.1.0`；
- 删除：`style/` 目录、`__pycache__`。

## 5. 验证

离屏脚本实例化 MainWidget 并触发转换逻辑（`temp/verify_batch1.py text_formatting` 必须 PASS）；冒烟调用 Service 方法确认业务逻辑未破坏。
