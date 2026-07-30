"""
Framework API Demo 数据演示服务

演示 DataProvider 接口（注册/注销插件、私有/公共数据读写、资源文件）。
"""

import hashlib
from typing import Any, Dict, Optional

from core.data.data_provider import DataNamespace
from utils.logging_tools import get_name

from .base import Service, _load_config


class DataDemoService(Service):
    """演示 DataProvider 接口的服务类"""

    def __init__(self, plugin_id, services=None, data_provider=None):
        super().__init__(plugin_id, services=services, data_provider=data_provider)
        config = _load_config()
        demo_cfg = config.get("demo", {})
        prefix = demo_cfg.get("plugin_id_prefix", "demo-target")
        hex_len = demo_cfg.get("plugin_id_hex_length", 8)
        # 使用确定性哈希，确保服务重建后 demo_plugin_id 不变
        hash_val = hashlib.md5(plugin_id.encode()).hexdigest()[:hex_len]
        self.demo_plugin_id = f"{prefix}-{hash_val}"
        self._last_asset_path: Optional[str] = None

    def register_demo_plugin(self) -> Dict[str, Any]:
        """演示注册插件"""
        try:
            self.dp.register_plugin(self.demo_plugin_id, "DemoTarget")
            self.logger.info(get_name(), f"成功注册演示插件: {self.demo_plugin_id}")
            return {"success": True, "message": f"插件 {self.demo_plugin_id} 注册成功"}
        except Exception as e:
            self.logger.error(get_name(), f"注册插件失败: {e}")
            return {"success": False, "error": str(e)}

    def unregister_demo_plugin(self) -> Dict[str, Any]:
        """演示注销插件"""
        try:
            self.dp.unregister_plugin(self.demo_plugin_id)
            self.logger.info(get_name(), f"成功注销演示插件: {self.demo_plugin_id}")
            return {"success": True, "message": f"插件 {self.demo_plugin_id} 注销成功"}
        except Exception as e:
            self.logger.error(get_name(), f"注销插件失败: {e}")
            return {"success": False, "error": str(e)}

    def cleanup(self) -> None:
        """卸载清理：注销演示插件命名空间（异常仅记日志，不向外抛出）"""
        try:
            self.dp.unregister_plugin(self.demo_plugin_id)
            self.logger.info(get_name(), f"卸载清理：已注销演示插件 {self.demo_plugin_id}")
        except Exception as e:
            self.logger.error(get_name(), f"卸载清理：注销演示插件失败: {e}")

    def write_private_data(self, key: str, value: Any) -> Dict[str, Any]:
        """演示写入私有数据"""
        try:
            self.dp.set_plugin_data(self.plugin_id, key, value, DataNamespace.PRIVATE)
            return {"success": True, "message": f"写入私有数据成功: {key}={value}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_private_data(self, key: str, default: Any = None) -> Dict[str, Any]:
        """演示读取私有数据"""
        try:
            value = self.dp.get_plugin_data(self.plugin_id, key, DataNamespace.PRIVATE, default)
            return {"success": True, "value": value}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_public_data(self, key: str, value: Any) -> Dict[str, Any]:
        """演示写入公共数据"""
        try:
            self.dp.set_plugin_data(self.plugin_id, key, value, DataNamespace.PUBLIC)
            return {"success": True, "message": f"写入公共数据成功: {key}={value}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_public_data(self, key: str, default: Any = None) -> Dict[str, Any]:
        """演示读取公共数据"""
        try:
            value = self.dp.get_plugin_data(self.plugin_id, key, DataNamespace.PUBLIC, default)
            return {"success": True, "value": value}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_data(self) -> Dict[str, Any]:
        """演示获取所有数据"""
        try:
            private_data = self.dp.get_all_plugin_data(self.plugin_id, DataNamespace.PRIVATE)
            public_data = self.dp.get_all_plugin_data(self.plugin_id, DataNamespace.PUBLIC)
            return {"success": True, "private": private_data, "public": public_data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_demo_asset(self) -> Dict[str, Any]:
        """演示保存资源文件"""
        try:
            content = b"Demo asset content"
            relative_path = self.dp.save_asset(self.plugin_id, "demo.txt", content)
            self._last_asset_path = relative_path
            return {"success": True, "path": relative_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_demo_asset(self, relative_path: str = None) -> Dict[str, Any]:
        """演示加载资源文件"""
        try:
            default_path = f"assets/plugins/{self.plugin_id}/demo.txt"
            path = relative_path or self._last_asset_path or default_path
            content = self.dp.load_asset(path)
            return {"success": True, "content": content.decode()}
        except Exception as e:
            return {"success": False, "error": str(e)}
