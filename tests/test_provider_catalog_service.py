"""Provider catalog response service tests."""

from services.core.provider_catalog_service import (
    build_campaign_packs_response,
    build_provider_catalog_response,
)


def test_build_provider_catalog_response_enriches_models_and_styles():
    providers = {
        "gemini": {
            "name": "Gemini",
            "models": [{"id": "gemini/flash"}, {"id": "gemini/pro"}],
        },
        "empty": {"name": "Empty", "models": []},
        "missing": {"name": "Missing"},
    }

    payload = build_provider_catalog_response(
        providers=providers,
        styles=[("summary", "요약"), ("detailed", "상세")],
        supadata_api_key="secret",
    )

    assert payload["providers"]["gemini"]["model_count"] == 2
    assert payload["providers"]["gemini"]["default_model"] == "gemini/flash"
    assert payload["providers"]["empty"]["model_count"] == 0
    assert payload["providers"]["empty"]["default_model"] is None
    assert payload["providers"]["missing"]["model_count"] == 0
    assert payload["providers"]["missing"]["default_model"] is None
    assert payload["styles"] == [
        {"id": "summary", "name": "요약"},
        {"id": "detailed", "name": "상세"},
    ]
    assert payload["supadataConfigured"] is True
    assert payload["hasAutoFallback"] is True


def test_build_provider_catalog_response_does_not_mutate_provider_input():
    providers = {"gemini": {"models": [{"id": "gemini/flash"}]}}

    build_provider_catalog_response(
        providers=providers,
        styles=[],
        supadata_api_key="",
    )

    assert providers == {"gemini": {"models": [{"id": "gemini/flash"}]}}


def test_build_campaign_packs_response_adds_id_to_each_pack():
    payload = build_campaign_packs_response(
        {
            "launch": {"name": "Launch", "styles": ["summary"]},
            "retention": {"name": "Retention"},
        }
    )

    assert payload == {
        "packs": {
            "launch": {"id": "launch", "name": "Launch", "styles": ["summary"]},
            "retention": {"id": "retention", "name": "Retention"},
        }
    }
