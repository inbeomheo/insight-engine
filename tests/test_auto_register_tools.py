"""Regression tests for content/export auto-registered tool schemas."""
from __future__ import annotations

import types
from unittest.mock import Mock


def test_content_collection_arguments_are_registered_as_arrays():
    from agent.registry import registry
    from agent.tools import content_tools  # noqa: F401

    expected_items = {
        ("generate_brief", "keywords"): {"type": "string"},
        ("build_source_receipts", "citations"): {"type": "object"},
        ("categorize_events", "events"): {"type": "object"},
        ("generate_outline", "keywords"): {},
        ("generate_summary_card", "key_points"): {"type": "string"},
    }

    for (tool_name, parameter_name), item_schema in expected_items.items():
        entry = registry.get(tool_name)
        assert entry is not None, tool_name
        assert entry.toolset == "content"
        assert entry.parameters["properties"][parameter_name] == {
            "type": "array",
            "items": item_schema,
        }


def test_quiz_tool_uses_json_safe_generator_instead_of_dataclass_input():
    import json

    from agent.registry import registry
    from agent.tools import content_tools  # noqa: F401

    assert registry.get("calculate_results") is None
    entry = registry.get("generate_quiz")
    assert entry is not None
    assert entry.parameters["properties"]["content"] == {"type": "string"}

    payload = json.loads(entry.handler({
        "content": "인사이트 엔진은 긴 영상을 구조화된 학습 자료로 변환합니다.",
        "num_questions": 1,
    }))
    assert payload["questions"]
    assert isinstance(payload["questions"][0], dict)


def test_export_object_and_boolean_arguments_keep_resolved_types():
    from agent.registry import registry
    from agent.tools import export_tools  # noqa: F401

    entry = registry.get("export_markdown")
    assert entry is not None
    assert entry.toolset == "export"

    properties = entry.parameters["properties"]
    assert properties["frontmatter"] == {"type": "object"}
    assert properties["metadata"] == {"type": "object"}
    assert properties["include_separator"] == {"type": "boolean"}
    assert entry.parameters["required"] == ["title", "content"]


def _module_with_two_public_functions(module_name: str) -> types.ModuleType:
    module = types.ModuleType(module_name)

    def zebra(value: str):
        return value

    def alpha(values: list[str]):
        return values

    zebra.__module__ = module_name
    alpha.__module__ = module_name
    module.zebra = zebra
    module.alpha = alpha
    return module


def test_auto_registration_preserves_module_skips_and_first_public_function(
    monkeypatch,
):
    from agent.tools import content_tools, export_tools

    assert content_tools._SKIP_MODULES == {"multi_source_collector"}
    assert content_tools._SKIP_FUNCTIONS == {
        "quiz_generator_service": {"calculate_results"},
    }
    assert export_tools._SKIP_MODULES == set()

    cases = (
        (
            content_tools,
            "services.content",
            "content",
            [(None, "multi_source_collector", False), (None, "sample", False)],
        ),
        (
            export_tools,
            "services.export",
            "export",
            [(None, "_private", False), (None, "sample", False)],
        ),
    )

    for wrapper, package, toolset, discovered_modules in cases:
        imported_modules = []
        registrations = []
        fake_module = _module_with_two_public_functions(f"{package}.sample")

        with monkeypatch.context() as patch:
            patch.setattr(
                wrapper.pkgutil,
                "iter_modules",
                lambda _paths, modules=discovered_modules: modules,
            )

            def fake_import(module_name):
                imported_modules.append(module_name)
                assert module_name == f"{package}.sample"
                return fake_module

            patch.setattr(wrapper.importlib, "import_module", fake_import)
            patch.setattr(
                wrapper.registry,
                "register",
                lambda **registration: registrations.append(registration),
            )
            wrapper._register_tools()

        assert imported_modules == [f"{package}.sample"]
        assert [registration["name"] for registration in registrations] == ["alpha"]
        assert registrations[0]["toolset"] == toolset
        assert registrations[0]["parameters"]["properties"]["values"] == {
            "type": "array",
            "items": {"type": "string"},
        }


def test_content_user_scope_is_hidden_and_forced_from_authenticated_dispatch(
    monkeypatch,
):
    import json

    from agent.registry import registry
    from agent.tools import content_tools  # noqa: F401
    from services.content import note_index_service, note_service

    find_entry = registry.get("find_notes_by_source_url")
    related_entry = registry.get("get_related_notes")
    assert find_entry is not None
    assert related_entry is not None

    for entry in (find_entry, related_entry):
        assert "owner_id" not in entry.parameters["properties"]
        assert "user_id" not in entry.parameters["properties"]
        assert "owner_id" not in entry.parameters["required"]
        assert "user_id" not in entry.parameters["required"]

    list_notes = Mock(return_value=[])
    monkeypatch.setattr(note_service, "list_notes", list_notes)
    find_result = json.loads(registry.dispatch(
        "find_notes_by_source_url",
        {
            "source": {
                "type": "article",
                "url": "https://example.com/source",
                "title": "Source",
            },
            "owner_id": "victim-user",
            "user_id": "victim-user",
        },
        user_id="authenticated-user",
    ))
    assert find_result == []
    list_notes.assert_called_once_with(owner_id="authenticated-user")

    collection = Mock()
    collection.count.return_value = 0
    owner_scope_for = Mock(return_value="authenticated-scope")
    monkeypatch.setattr(note_index_service, "_get_collection", lambda: collection)
    monkeypatch.setattr(note_index_service, "owner_scope_for", owner_scope_for)
    related_result = json.loads(registry.dispatch(
        "get_related_notes",
        {
            "note": {"id": "note-1", "summary": "summary"},
            "owner_id": "victim-user",
            "user_id": "victim-user",
            "limit": 3,
        },
        user_id="authenticated-user",
    ))
    assert related_result == []
    owner_scope_for.assert_called_once_with("authenticated-user")


def test_content_user_scoped_tools_fail_closed_without_authenticated_dispatch(
    monkeypatch,
):
    import json

    from agent.registry import registry
    from agent.tools import content_tools  # noqa: F401
    from services.content import note_index_service, note_service

    list_notes = Mock(return_value=[])
    monkeypatch.setattr(note_service, "list_notes", list_notes)

    result = json.loads(registry.dispatch(
        "find_notes_by_source_url",
        {
            "source": {
                "type": "article",
                "url": "https://example.com/source",
                "title": "Source",
            },
            "owner_id": "victim-user",
        },
    ))

    assert result["code"] == "TOOL_EXECUTION_FAILED"
    list_notes.assert_not_called()

    get_collection = Mock()
    monkeypatch.setattr(note_index_service, "_get_collection", get_collection)
    related_result = json.loads(registry.dispatch(
        "get_related_notes",
        {
            "note": {"id": "note-1", "summary": "summary"},
            "owner_id": "victim-user",
        },
    ))

    assert related_result["code"] == "TOOL_EXECUTION_FAILED"
    get_collection.assert_not_called()
