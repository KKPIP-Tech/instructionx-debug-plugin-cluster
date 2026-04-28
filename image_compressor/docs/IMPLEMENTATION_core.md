# 图片压缩插件 — 核心实现文档

## 架构
| 文件 | 职责 |
|------|------|
| `entrance.py` | 胶水层：实例化 `CoreService` + `MainWidget` |
| `function/services/core_service.py` | 图片压缩逻辑（Pillow） |
| `ui/main_widget.py` | 文件选择、质量滑块、压缩按钮、结果展示 |
| `config/default.json` | 默认质量与质量范围配置 |

## 核心类
### `CoreService`
- `compress_image(input_path, output_path, quality)`：使用 Pillow 进行有损/无损压缩。
- `get_image_info(path)`：获取图片尺寸、格式、大小信息。

## 关键设计决策
1. 压缩质量参数直接映射到 Pillow 的 `quality` 参数（仅对 JPEG/WEBP 有效）。
2. PNG 压缩使用优化模式而非质量参数。
3. 压缩在后台线程执行，避免阻塞主 UI。

## 配置
`config/default.json` 中：
- `compression.default_quality`: 默认压缩质量（85）
- `compression.quality_range`: 质量滑块范围 [1, 100]
