"""
Framework API Demo 框架信息服务

提供框架版本与可用 API 清单信息，并演示框架 utils 工具：
LoggerManager 五级日志、thread_utils 线程封送、FontMap 字体查询、
load_image_as_base64 图片转 Base64。
"""

import base64
from typing import Any, Callable, Dict

from core.version import get_instructionx_version_string
from utils.font_map import FontFamily, FontInfo, FontMap, FontVariant
from utils.image_utils import load_image_as_base64
from utils.logging_tools import get_name
from utils.thread_utils import is_ui_thread, run_in_ui_thread, run_in_ui_thread_sync

from .base import Service

# 演示用最小图片：1x1 透明 PNG（base64 常量，模块加载时解码为字节串）
_DEMO_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
    "AAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
_DEMO_PNG_BYTES: bytes = base64.b64decode(_DEMO_PNG_BASE64)

# 演示图片保存到 DataProvider 资源区时使用的文件名
_DEMO_IMAGE_FILENAME = "thread_demo_pixel.png"

# 返回结果中展示的 base64 前缀长度
_BASE64_PREFIX_LENGTH = 32

# 线程封送演示任务的名称
_THREAD_DEMO_TASK_NAME = "thread_marshal_demo"


class FrameworkInfoService(Service):
    """获取框架信息并演示 utils 工具的服务类"""

    def get_framework_info(self) -> Dict[str, Any]:
        """获取框架信息"""
        return {
            "framework": "InstructionX",
            "version": get_instructionx_version_string(),
            "apis": [
                "DataProvider",
                "BackgroundTaskManager",
                "LLMProvider",
                "PluginManager",
                "LoggerManager",
            ],
        }

    # ------------------------------------------------------------------
    #  LoggerManager 日志级别演示
    # ------------------------------------------------------------------

    def demo_log_levels(self) -> Dict[str, Any]:
        """演示 LoggerManager 五级日志：依次写入 debug/info/warning/error/critical

        返回:
            包含已写入级别列表的字典；日志内容请查看 logs/application.log
        """
        module = get_name()
        levels = ["debug", "info", "warning", "error", "critical"]
        for level in levels:
            log_func = getattr(self.logger, level)
            log_func(module, f"日志级别演示: 这是一条 {level.upper()} 级别日志")
        return {
            "success": True,
            "levels": levels,
            "message": "五级日志已写入，请到 logs/application.log 查看",
        }

    # ------------------------------------------------------------------
    #  thread_utils 线程封送演示
    # ------------------------------------------------------------------

    def demo_thread_utils(self) -> Dict[str, Any]:
        """演示 is_ui_thread / run_in_ui_thread / run_in_ui_thread_sync

        在调用线程记录 is_ui_thread()；再注册同步任务到工作线程执行
        _worker_probe（其中经 run_in_ui_thread_sync 封送回 UI 线程取对照值，
        并经 run_in_ui_thread 异步封送一条回执），结果经 notifier 上抛。

        返回:
            包含调用方线程判定结果与任务 id 的字典
        """
        caller_is_ui = is_ui_thread()
        try:
            task_id = self.tm.register_sync_task(
                plugin_id=self.plugin_id,
                name=_THREAD_DEMO_TASK_NAME,
                func=self._worker_probe,
                callback=self._make_thread_callback(),
            )
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {
            "success": True,
            "task_id": task_id,
            "caller_is_ui_thread": caller_is_ui,
            "message": "工作线程封送对照结果将经事件通知回传（见日志面板）",
        }

    def _worker_probe(self) -> Dict[str, Any]:
        """工作线程探针：对照「工作线程直判」与「封送到 UI 线程执行」的结果"""
        worker_is_ui = is_ui_thread()
        marshaled_is_ui = run_in_ui_thread_sync(is_ui_thread)
        run_in_ui_thread(
            self._notify_event,
            "run_in_ui_thread 异步封送回执：本条事件由 UI 线程上抛",
        )
        return {
            "worker_is_ui_thread": worker_is_ui,
            "marshaled_is_ui_thread": marshaled_is_ui,
        }

    def _make_thread_callback(self) -> Callable:
        """构造线程演示任务的完成回调（工作线程执行）：经 notifier 上抛，异常仅记日志"""

        def on_completed(task_id: str, status, result, error) -> None:
            try:
                self._notify_event(f"线程封送对照 [{status}]: {result} 错误={error}")
            except Exception as e:
                self.logger.error(get_name(), f"线程演示回调处理失败: {e}")

        return on_completed

    # ------------------------------------------------------------------
    #  FontMap 字体查询演示
    # ------------------------------------------------------------------

    def demo_font_map(self) -> Dict[str, Any]:
        """演示 FontMap.all_fonts() 与 FontMap.get() 字体查询

        返回:
            可用字体清单（family/variant/weight/relative_path）与一个示例 FontInfo
        """
        fonts = FontMap.all_fonts()
        sample = FontMap.get(FontFamily.SMILEY_SANS, FontVariant.OBLIQUE)
        return {
            "success": True,
            "font_count": len(fonts),
            "fonts": [self._font_info_to_dict(f) for f in fonts],
            "sample": self._font_info_to_dict(sample) if sample else None,
        }

    @staticmethod
    def _font_info_to_dict(info: FontInfo) -> Dict[str, Any]:
        """把 FontInfo 转换为可 JSON 序列化的字典"""
        return {
            "family": info.family.value,
            "variant": info.variant.value,
            "weight": info.weight,
            "relative_path": info.relative_path,
            "absolute_path": info.absolute_path,
        }

    # ------------------------------------------------------------------
    #  load_image_as_base64 图片转 Base64 演示
    # ------------------------------------------------------------------

    def demo_load_image_base64(self) -> Dict[str, Any]:
        """演示 image_utils.load_image_as_base64

        先用 DataProvider.save_asset 保存一张 1x1 透明 PNG，
        再经 get_asset_path 取绝对路径（load_image_as_base64 接收文件系统路径）
        读回为 base64。

        返回:
            资源相对路径、base64 长度与前缀；失败时 success=False 与 error
        """
        try:
            rel_path = self.dp.save_asset(
                self.plugin_id, _DEMO_IMAGE_FILENAME, _DEMO_PNG_BYTES
            )
            abs_path = self.dp.get_asset_path(rel_path)
            encoded = load_image_as_base64(abs_path)
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {
            "success": True,
            "asset_path": rel_path,
            "base64_length": len(encoded),
            "base64_prefix": encoded[:_BASE64_PREFIX_LENGTH],
        }
