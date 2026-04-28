# 单位转换插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：实例化 `CoreService` + `MainWidget` |
| `function/services/core_service.py` | 单位转换算法与换算表 |
| `ui/main_widget.py` | 量纲选择、单位下拉框、输入输出 UI |
| `config/default.json` | 插件元数据与支持的单位列表 |

## 核心类
### `CoreService`
- `convert_length(value, from_unit, to_unit)`：基于基准单位（米）的换算。
- `convert_temperature(value, from_unit, to_unit)`：C/F/K 公式转换。

## 关键设计决策
1. 长度转换使用"以米为基准"的系数表，避免 N² 换算矩阵。
2. 温度转换因公式非线性，单独处理。

## 配置
`config/default.json` 中 `units.length` 和 `units.temperature` 定义了支持的单位列表。
