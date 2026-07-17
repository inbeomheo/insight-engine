import inspect
import json
import logging
from types import ModuleType
from unittest.mock import patch

from agent.tools import _auto_register
from agent.tools._auto_register import (
    build_params_schema,
    find_main_function,
    make_handler,
    register_service_tools,
)


class RecordingRegistry:
    def __init__(self):
        self.entries = []

    def register(self, **entry):
        self.entries.append(entry)


def test_build_params_schema_supports_common_annotations_and_skips_variadics():
    def sample(content: str, limit: int, scores: list[str], enabled: bool = False, **kwargs):
        return content, limit, scores, enabled, kwargs

    schema = build_params_schema(inspect.signature(sample))

    assert schema == {
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "limit": {"type": "integer"},
            "scores": {"type": "array", "items": {"type": "string"}},
            "enabled": {"type": "boolean"},
        },
        "required": ["content", "limit", "scores"],
    }


def test_build_params_schema_uses_configured_content_fallback():
    def no_parameters():
        return None

    schema = build_params_schema(
        inspect.signature(no_parameters),
        default_content_description="분석할 텍스트",
    )

    assert schema["properties"] == {
        "content": {"type": "string", "description": "분석할 텍스트"}
    }
    assert schema["required"] == ["content"]


def test_find_main_function_ignores_private_and_reexported_functions():
    module = ModuleType("services.fake.sample")

    def public(value):
        return value

    def external(value):
        return value

    public.__module__ = module.__name__
    external.__module__ = "services.other"
    module._private = public
    module.external = external
    module.public = public

    assert find_main_function(module) is public


def test_make_handler_filters_arguments_and_serializes_results_and_errors():
    def success(content, limit=1):
        return {"content": content, "limit": limit}

    handler = make_handler(
        success,
        ["content", "limit"],
        logger=logging.getLogger("test"),
        toolset="test",
    )
    assert json.loads(handler({"content": "hello", "ignored": True})) == {
        "content": "hello",
        "limit": 1,
    }

    def failure():
        raise ValueError("boom")

    failure_handler = make_handler(
        failure,
        [],
        logger=logging.getLogger("test"),
        toolset="test",
    )
    assert json.loads(failure_handler({})) == {"error": "boom"}


def test_register_service_tools_registers_first_public_function_per_module():
    package = ModuleType("services.fake")
    package.__path__ = ["/virtual/services/fake"]
    module = ModuleType("services.fake.alpha")

    def analyze(content: str, limit: int = 5):
        """가상 서비스 분석."""
        return {"content": content, "limit": limit}

    analyze.__module__ = module.__name__
    module.analyze = analyze
    target = RecordingRegistry()

    def import_module(name):
        if name == "services.fake":
            return package
        if name == "services.fake.alpha":
            return module
        raise ModuleNotFoundError(name)

    with patch.object(_auto_register.importlib, "import_module", side_effect=import_module), patch.object(
        _auto_register.pkgutil,
        "iter_modules",
        return_value=[(None, "alpha", False), (None, "_private", False), (None, "nested", True)],
    ):
        count = register_service_tools(
            "services.fake",
            "fake",
            target_registry=target,
        )

    assert count == 1
    assert len(target.entries) == 1
    entry = target.entries[0]
    assert entry["name"] == "analyze"
    assert entry["toolset"] == "fake"
    assert entry["description"] == "가상 서비스 분석."
    assert json.loads(entry["handler"]({"content": "text"})) == {
        "content": "text",
        "limit": 5,
    }


def test_register_service_tools_returns_zero_for_missing_package():
    with patch(
        "agent.tools._auto_register.importlib.import_module",
        side_effect=ModuleNotFoundError("missing"),
    ):
        assert register_service_tools("services.missing", "missing") == 0
