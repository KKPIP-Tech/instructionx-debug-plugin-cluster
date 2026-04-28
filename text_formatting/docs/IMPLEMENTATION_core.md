# 文本格式化插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：实例化 `CoreService` + `MainWidget` |
| `function/services/core_service.py` | 文本格式化纯函数 |
| `ui/main_widget.py` | 输入区、操作按钮、输出区 |
| `config/default.json` | 插件元数据与 UI 间距配置 |

## 核心类
### `CoreService`
- `to_upper(text)`、`to_lower(text)`、`to_title(text)`：大小写转换。
- `trim(text)`、`remove_all_spaces(text)`、`remove_extra_spaces(text)`：空格处理。

## 关键设计决策
1. 所有格式化方法为纯函数，无副作用，便于测试。
2. UI 采用双栏布局：输入在上，操作按钮在中，输出在下。

## 配置
参见 `config/default.json`。
