# 代码格式化插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：实例化 `CoreService` + `MainWidget` |
| `function/services/core_service.py` | 代码格式化逻辑（调用 black/prettier 或内置格式化） |
| `ui/main_widget.py` | 语言选择、代码输入区、格式化按钮、输出区 |
| `config/default.json` | 插件元数据与支持的语言列表 |

## 核心类
### `CoreService`
- `format_python(code)`：Python 代码格式化。
- `format_javascript(code)`：JavaScript 代码格式化。
- `format(code, language)`：根据语言分发到对应格式化器。

## 关键设计决策
1. 格式化器以字典形式注册，便于扩展新语言。
2. 格式化失败时返回原始代码并附带错误信息，避免数据丢失。

## 配置
`config/default.json` 中 `languages` 定义了当前支持的语言列表。
