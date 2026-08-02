# -*- coding: utf-8 -*-
"""ui_demo 插件元数据契约测试。

覆盖范围：
- ``UiDemoPluginInfo`` 的 IPluginInfo 抽象契约（version/plugin_type_id/
  developer 等必填属性）；
- ``service_api`` 声明结构与 ``service.py`` Service 实现的一致性
  （声明的方法存在且可调用，Service 公开方法全部被声明）。
"""

from core.plugin.plugin_version import PluginVersion, VersionType

from plugin.ui_demo.information import UiDemoPluginInfo
from plugin.ui_demo.service import Service


class TestPluginInfoContract:
    """IPluginInfo 抽象属性的基本契约。"""

    def setup_method(self) -> None:
        """每个用例构造独立的元数据实例。"""
        self.info = UiDemoPluginInfo()

    def test_version_is_release_1_0_2(self) -> None:
        """版本号应为 release.1.0.2 的正式版 PluginVersion。"""
        version = self.info.version
        assert isinstance(version, PluginVersion)
        assert version.version_type is VersionType.RELEASE
        assert (version.major, version.minor, version.patch) == (1, 0, 2)
        assert str(version) == "release.1.0.2"

    def test_plugin_type_id(self) -> None:
        """插件类型标识应为 ui-demo（与目录名对应的 kebab-case）。"""
        assert self.info.plugin_type_id == "ui-demo"

    def test_required_text_fields_non_empty(self) -> None:
        """开发者、邮箱、网站、描述、技能描述均应为非空字符串。"""
        for value in (
            self.info.developer,
            self.info.developer_email,
            self.info.developer_website,
            self.info.description,
            self.info.skill_description,
        ):
            assert isinstance(value, str)
            assert value.strip(), "必填文本字段不允许为空白"

    def test_is_free_and_dependencies(self) -> None:
        """组件橱窗为免费插件且不声明第三方依赖。"""
        assert self.info.is_free is True
        assert self.info.dependencies == {}

    def test_tags_is_string_list(self) -> None:
        """tags 应为非空字符串列表且不含重复项。"""
        tags = self.info.tags
        assert isinstance(tags, list) and tags
        assert all(isinstance(tag, str) and tag for tag in tags)
        assert len(tags) == len(set(tags))

    def test_skill_icon_available(self) -> None:
        """skill_icon 应返回内置图标（PluginIcon 实例，非 None）。"""
        icon = self.info.skill_icon
        assert icon is not None


class TestServiceApiConsistency:
    """service_api 声明与 Service 实现的一致性。"""

    def setup_method(self) -> None:
        """每个用例准备元数据与无参 Service 实例。"""
        self.info = UiDemoPluginInfo()
        self.service = Service()

    def test_service_api_structure(self) -> None:
        """service_api 每个条目应含 description/parameters/returns 三段。"""
        api = self.info.service_api
        assert isinstance(api, dict) and api, "service_api 不允许为空"
        for name, desc in api.items():
            assert isinstance(name, str) and not name.startswith("_")
            assert isinstance(desc.get("description"), str) and desc["description"]
            assert isinstance(desc.get("parameters"), dict)
            assert isinstance(desc.get("returns"), dict)

    def test_declares_get_control_list(self) -> None:
        """应声明 get_control_list，且 returns.type 为 list。"""
        api = self.info.service_api
        assert "get_control_list" in api
        entry = api["get_control_list"]
        assert entry["parameters"] == {}, "无参方法不应声明多余参数"
        assert entry["returns"]["type"] == "list"

    def test_declared_methods_exist_on_service(self) -> None:
        """service_api 声明的每个方法在 Service 实例上存在且可调用。"""
        for name in self.info.service_api:
            assert hasattr(self.service, name), f"Service 缺少已声明方法 {name}"
            assert callable(getattr(self.service, name))

    def test_service_public_methods_all_declared(self) -> None:
        """Service 的公开方法应全部被 service_api 声明（无遗漏对外接口）。"""
        declared = set(self.info.service_api)
        public_methods = {
            name for name in dir(self.service)
            if not name.startswith("_") and callable(getattr(self.service, name))
        }
        assert public_methods == declared
