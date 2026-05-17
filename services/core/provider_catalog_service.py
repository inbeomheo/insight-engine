"""Provider catalog response builders."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _enrich_provider(provider: Mapping[str, Any]) -> dict[str, Any]:
    models = provider.get("models", [])
    return {
        **provider,
        "model_count": len(models),
        "default_model": models[0]["id"] if models else None,
    }


def build_provider_catalog_response(
    *,
    providers: Mapping[str, Mapping[str, Any]],
    styles: Sequence[Sequence[Any]],
    supadata_api_key: str | None,
) -> dict[str, Any]:
    """Build the JSON body for `/api/providers`."""
    return {
        "providers": {
            provider_id: _enrich_provider(provider)
            for provider_id, provider in providers.items()
        },
        "styles": [
            {"id": style[0], "name": style[1]}
            for style in styles
        ],
        "supadataConfigured": bool(supadata_api_key),
        "hasAutoFallback": True,
    }


def build_campaign_packs_response(
    campaign_packs: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Build the JSON body for `/api/providers/campaign-packs`."""
    return {
        "packs": {
            pack_id: {**pack, "id": pack_id}
            for pack_id, pack in campaign_packs.items()
        }
    }
