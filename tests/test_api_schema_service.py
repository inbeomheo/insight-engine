"""API schema response service tests."""

from services.data.api_schema_service import build_api_schema


def test_build_api_schema_returns_current_route_contract():
    schema = build_api_schema()

    assert schema["openapi"] == "3.0.0"
    assert schema["info"] == {"title": "Insight Engine API", "version": "1.0.0"}
    assert list(schema["paths"].keys()) == ["/generate"]


def test_build_api_schema_describes_generate_request_shape():
    schema = build_api_schema()
    request_schema = schema["paths"]["/generate"]["post"]["requestBody"]["content"]["application/json"]["schema"]

    assert schema["paths"]["/generate"]["post"]["summary"] == "AI ??? ??"
    assert request_schema["type"] == "object"
    assert request_schema["required"] == ["url", "model", "style"]
    assert request_schema["properties"]["url"] == {
        "type": "string",
        "description": "YouTube ?? URL",
    }
    assert request_schema["properties"]["model"] == {
        "type": "string",
        "description": "AI ?? ID",
    }
    assert request_schema["properties"]["style"] == {
        "type": "string",
        "description": "??? ??? ID",
    }


def test_build_api_schema_describes_generate_optional_modifiers():
    schema = build_api_schema()
    properties = schema["paths"]["/generate"]["post"]["requestBody"]["content"]["application/json"]["schema"]["properties"]
    modifier_properties = properties["modifiers"]["properties"]

    assert modifier_properties["length"] == {
        "type": "string",
        "enum": ["short", "medium", "long"],
    }
    assert modifier_properties["writing_style"] == {
        "type": "string",
        "enum": ["conversational", "explanatory", "casual", "expert"],
    }
    assert modifier_properties["language"] == {
        "type": "string",
        "enum": ["ko", "en", "ja"],
    }
    assert properties["detail_level"] == {
        "type": "string",
        "enum": ["brief", "standard", "deep"],
        "default": "standard",
    }
    assert properties["output_format"] == {
        "type": "string",
        "enum": ["html", "markdown", "plain"],
        "default": "html",
    }
    assert properties["max_chars"] == {
        "type": "integer",
        "minimum": 100,
        "maximum": 50000,
    }
    assert properties["include_transcript"] == {"type": "boolean", "default": False}
    assert properties["web_search"] == {"type": "boolean", "default": False}
    assert properties["agent_mode"] == {"type": "boolean", "default": False}
