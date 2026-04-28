# 本地 HTTP 服务器插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 服务器生命周期管理（HTTPServer、线程、SignalHolder）、UI 控制 |
| `function/services/core_service.py` | DataProvider 数据持久化（端口、请求数、运行状态） |
| `config/default.json` | 默认端口与端口范围配置 |

## 核心类
### `RequestHandler` (BaseHTTPRequestHandler)
- `do_GET()` / `do_POST()`：处理 HTTP 请求，返回 JSON 响应。
- `log_message()`：重写为空以抑制默认日志输出。

### `SignalHolder` (QObject)
- `status_changed` Signal：跨线程通信，将服务器事件传递到主线程 UI。

### `Service`
- `increment_request_count()`：原子性增加请求计数并持久化到 DataProvider。
- `set_running()`、`save_data()`、`load_data()`：状态持久化。

## 关键设计决策
1. 使用 `BackgroundTaskManager.register_long_running_task()` 管理服务器线程，支持崩溃后自动恢复。
2. `RequestHandler.on_request_callback` 为类变量，用于从服务器线程回调到插件实例。
3. 端口和请求计数通过 DataProvider 持久化，支持跨会话状态恢复。

## 配置
`config/default.json` 中：
- `server.default_port`: 默认端口（8080）
- `server.port_range`: 有效端口范围 [1024, 65535]
