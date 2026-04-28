# 颜色转换插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：实例化 `CoreService` + `MainWidget` |
| `function/services/core_service.py` | 颜色转换算法（HEX ↔ RGB ↔ HSL） |
| `ui/main_widget.py` | 输入框、转换按钮、结果展示的 UI 布局 |
| `config/default.json` | 插件元数据与 UI 间距配置 |

## 核心类
### `CoreService`
- `hex_to_rgb(hex_str)`：解析 HEX 字符串为 RGB 元组。
- `rgb_to_hex(r, g, b)`：将 RGB 元组格式化为 HEX。
- `rgb_to_hsl(r, g, b)`：RGB → HSL 数学转换。

## 关键设计决策
1. 转换算法为纯函数，无状态，便于单元测试。
2. UI 采用垂直分组布局，每种转换类型一个 `QGroupBox`。

## 配置
参见 `config/default.json`，包含 UI 边距和间距配置。
