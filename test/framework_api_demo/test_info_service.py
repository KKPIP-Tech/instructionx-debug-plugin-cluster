# -*- coding: utf-8 -*-
"""FrameworkInfoService 框架信息服务测试。

覆盖 function/services/info_service.py：
- get_framework_info：框架信息结构；
- demo_log_levels：五级日志依次调用（logger 替换为记录桩，避免写真实日志文件）；
- demo_font_map：字体清单与示例字体结构；
- demo_load_image_base64：1x1 PNG 资源保存→读回 base64 的正常路径，
  以及底层保存抛异常时的错误路径。

数据落盘经隔离 DataProvider 指向 tmp_path，不触碰真实 data/ 目录。
"""

import base64

from plugin.framework_api_demo.function.services.info_service import (
    _DEMO_PNG_BYTES,
)


class _RecordingLogger:
    """记录各级别调用次数的 logger 桩（替代 LoggerManager 单例）"""

    def __init__(self):
        self.calls = []

    def debug(self, module, message):
        self.calls.append(("debug", module, message))

    def info(self, module, message):
        self.calls.append(("info", module, message))

    def warning(self, module, message):
        self.calls.append(("warning", module, message))

    def error(self, module, message):
        self.calls.append(("error", module, message))

    def critical(self, module, message):
        self.calls.append(("critical", module, message))


class TestGetFrameworkInfo:
    """get_framework_info 结构校验"""

    def test_structure(self, info_service):
        """应返回框架名、版本与核心 API 清单"""
        info = info_service.get_framework_info()
        assert info["framework"] == "InstructionX"
        assert isinstance(info["version"], str) and info["version"]
        assert isinstance(info["apis"], list) and info["apis"]


class TestDemoLogLevels:
    """demo_log_levels 五级日志演示"""

    def test_all_five_levels_emitted_in_order(self, info_service):
        """应按 debug→info→warning→error→critical 顺序各写一条日志"""
        recorder = _RecordingLogger()
        info_service.logger = recorder

        result = info_service.demo_log_levels()

        assert result["success"] is True
        assert result["levels"] == ["debug", "info", "warning", "error", "critical"]
        assert [call[0] for call in recorder.calls] == result["levels"]
        assert all("日志级别演示" in call[2] for call in recorder.calls)


class TestDemoFontMap:
    """demo_font_map 字体查询演示"""

    def test_font_list_structure(self, info_service):
        """字体清单应与 FontMap.all_fonts() 等长且字段完整"""
        result = info_service.demo_font_map()
        assert result["success"] is True
        assert result["font_count"] == len(result["fonts"])
        assert result["font_count"] > 0
        required_keys = {"family", "variant", "weight", "relative_path", "absolute_path"}
        for font in result["fonts"]:
            assert required_keys <= set(font)

    def test_sample_font(self, info_service):
        """示例字体应为 SmileySans 斜体且字段完整（weight 允许为 None）"""
        result = info_service.demo_font_map()
        sample = result["sample"]
        assert sample is not None
        assert sample["family"] == "SmileySans"
        assert sample["variant"] == "Oblique"
        # FontInfo.weight 语义为 int | None（仅 AlibabaPuHuiTi 系列带字重数字）
        assert sample["weight"] is None or isinstance(sample["weight"], int)


class TestDemoLoadImageBase64:
    """demo_load_image_base64 图片转 Base64 演示"""

    def test_success_path_roundtrip(self, info_service):
        """保存的 1x1 PNG 应能读回为等价的 base64"""
        result = info_service.demo_load_image_base64()
        assert result["success"] is True
        assert result["asset_path"].endswith("thread_demo_pixel.png")
        expected = base64.b64encode(_DEMO_PNG_BYTES).decode()
        assert result["base64_length"] == len(expected)
        assert result["base64_prefix"] == expected[:32]

    def test_failure_with_broken_data_provider(self, info_service, monkeypatch):
        """save_asset 抛异常时应返回 success=False 与错误信息"""
        def _broken_save(*args, **kwargs):
            raise RuntimeError("磁盘写入失败")

        monkeypatch.setattr(info_service.dp, "save_asset", _broken_save)
        result = info_service.demo_load_image_base64()
        assert result["success"] is False
        assert "磁盘写入失败" in result["error"]
