# -*- coding: utf-8 -*-
"""information.py 的 service_api 声明与 service.py 实现的一致性测试。

覆盖：
- service_api 声明的方法集合与 FrameworkApiDemoService 的公开实现逐方法对应；
- 每个方法的声明参数名与实现签名一致，required 标记与默认值有无一致；
- 声明结构完整（description/parameters/returns）；
- 插件元数据基本字段（版本、类型标识、免费标记、标签）。
"""

import inspect

from plugin.framework_api_demo.information import FrameworkAPIDemoPluginInfo
from plugin.framework_api_demo.service import FrameworkApiDemoService

# service_api 声明的三个方法名（契约清单）
EXPECTED_API_METHODS = {
    "demo_data_operation",
    "demo_task_operation",
    "get_framework_info",
}


class TestServiceApiDeclaration:
    """service_api 声明结构"""

    def test_declared_method_set(self):
        """声明的方法集合应恰为三个演示方法"""
        api = FrameworkAPIDemoPluginInfo().service_api
        assert set(api) == EXPECTED_API_METHODS

    def test_declaration_structure_complete(self):
        """每个声明都应包含 description/parameters/returns 三段"""
        api = FrameworkAPIDemoPluginInfo().service_api
        for name, declaration in api.items():
            assert declaration["description"], f"{name} 缺 description"
            assert isinstance(declaration["parameters"], dict), f"{name} 缺 parameters"
            assert "type" in declaration["returns"], f"{name} 缺 returns.type"


class TestDeclarationMatchesImplementation:
    """声明与实现逐方法一致"""

    def test_every_declared_method_implemented(self):
        """声明的每个方法在实现类上都应存在且可调用"""
        api = FrameworkAPIDemoPluginInfo().service_api
        for name in api:
            assert callable(getattr(FrameworkApiDemoService, name, None)), name

    def test_parameter_names_match_signature(self):
        """声明的参数名集合应与实现签名（除 self）完全一致"""
        api = FrameworkAPIDemoPluginInfo().service_api
        for name, declaration in api.items():
            signature = inspect.signature(getattr(FrameworkApiDemoService, name))
            impl_params = set(signature.parameters) - {"self"}
            declared_params = set(declaration["parameters"])
            assert impl_params == declared_params, (
                f"{name}: 实现参数 {impl_params} 与声明参数 {declared_params} 不一致"
            )

    def test_required_flags_match_defaults(self):
        """声明 required=True 的参数在实现中应无默认值，反之应有默认值"""
        api = FrameworkAPIDemoPluginInfo().service_api
        for name, declaration in api.items():
            signature = inspect.signature(getattr(FrameworkApiDemoService, name))
            for param_name, param_decl in declaration["parameters"].items():
                param = signature.parameters[param_name]
                has_default = param.default is not inspect.Parameter.empty
                assert param_decl["required"] == (not has_default), (
                    f"{name}.{param_name}: required={param_decl['required']} "
                    f"与实现默认值有无（{has_default}）矛盾"
                )


class TestPluginMetadata:
    """插件元数据基本字段"""

    def test_version_string(self):
        """版本应为 release.1.0.4"""
        version = FrameworkAPIDemoPluginInfo().version
        assert str(version) == "release.1.0.4"

    def test_plugin_type_id(self):
        """插件类型标识应稳定为 framework-api-demo"""
        assert FrameworkAPIDemoPluginInfo().plugin_type_id == "framework-api-demo"

    def test_is_free(self):
        """插件应标记为免费"""
        assert FrameworkAPIDemoPluginInfo().is_free is True

    def test_tags_non_empty(self):
        """标签应为非空列表"""
        tags = FrameworkAPIDemoPluginInfo().tags
        assert isinstance(tags, list) and tags
