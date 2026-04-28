# 颜色转换插件 — 产品需求文档

## 概述
提供常见颜色格式之间的相互转换，支持 HEX ↔ RGB ↔ HSL 等格式。

## 功能需求
- **HEX 转 RGB**：输入 6 位十六进制颜色码，输出 RGB 值。
- **RGB 转 HEX**：输入 RGB 值，输出 HEX 码。
- **RGB 转 HSL**：输入 RGB 值，输出 HSL 值。
- **实时预览**：转换结果即时显示。

## 非功能需求
- 输入校验：非法 HEX 码需给出友好提示。
- 性能：转换逻辑纯计算，响应延迟 < 10ms。

## 依赖
- `core.plugin.plugin_interface.IPlugin`
- `PySide6.QtWidgets`
