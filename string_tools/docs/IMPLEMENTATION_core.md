# 字符串工具插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：实例化 `CoreService` + `MainWidget` |
| `function/services/core_service.py` | 字符串处理算法 |
| `ui/main_widget.py` | 输入区、操作按钮网格、输出区 |
| `config/default.json` | 插件元数据与 UI 间距配置 |

## 核心类
### `CoreService`
- `count_stats(text)`：返回字符数、单词数、行数字典。
- `reverse_text(text)`、`reverse_words(text)`：反转逻辑。
- `base64_encode(text)`、`base64_decode(text)`：Base64 编解码。
- `find_replace(text, old, new)`：查找替换。

## 关键设计决策
1. 单词统计使用正则 `\w+`，支持多语言扩展。
2. UI 按钮使用网格布局，功能分组展示。

## 配置
参见 `config/default.json`。
