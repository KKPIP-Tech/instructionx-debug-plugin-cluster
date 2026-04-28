"""
图片压缩核心业务逻辑

提供图片压缩和信息获取功能，不依赖任何 UI 框架。
"""

import os
from utils.logging_tools import LoggerManager, get_name


class CoreService:
    """图片压缩核心服务"""

    _logger = LoggerManager()

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def compress_image(self, file_path: str, quality: int = 85) -> bool:
        """压缩图片"""
        try:
            if not os.path.exists(file_path):
                return False
            # from PIL import Image; img = Image.open(file_path); img.save(output_path, quality=quality)
            return True
        except Exception as e:
            self._logger.error(get_name(), f'Error compressing image: {e}')
            return False

    def get_image_info(self, file_path: str) -> dict:
        """获取图片信息"""
        try:
            if not os.path.exists(file_path):
                return {}
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            return {
                'file_path': file_path,
                'file_size': file_size_mb,
                'file_size_str': f"{file_size_mb:.2f} MB"
            }
        except Exception as e:
            self._logger.error(get_name(), f'Error getting image info: {e}')
            return {}
