# API Demo 插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：实例化 `ApiService` + `MainWidget` |
| `function/services/core_service.py` | 封装 PluginManager 的 API 发现与调用逻辑 |
| `ui/main_widget.py` | API 列表、方法详情、输入输出区域 |
| `config/default.json` | 插件元数据与 UI 间距配置 |

## 核心类
### `ApiService`
- `refresh_api_list()`：通过 `PluginManager` 获取所有插件的 API 列表。
- `execute_api(method_name, text_input)`：跨插件调用指定方法。

## 关键设计决策
1. Service 层封装 `PluginManager`，避免 UI 直接依赖框架内部类。
2. API 列表缓存，减少重复查询开销。

## 配置
参见 `config/default.json`。
