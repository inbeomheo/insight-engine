"""API schema response helpers."""

from __future__ import annotations

from typing import Any


def build_api_schema() -> dict[str, Any]:
    """Build the public API parameter OpenAPI schema."""
    return {
        "openapi": "3.0.0",
        "info": {"title": "Insight Engine API", "version": "1.0.0"},
        "paths": {
            "/generate": {
                "post": {
                    "summary": "AI ??? ??",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["url", "model", "style"],
                                    "properties": {
                                        "url": {
                                            "type": "string",
                                            "description": "YouTube ?? URL",
                                        },
                                        "model": {
                                            "type": "string",
                                            "description": "AI ?? ID",
                                        },
                                        "style": {
                                            "type": "string",
                                            "description": "??? ??? ID",
                                        },
                                        "modifiers": {
                                            "type": "object",
                                            "properties": {
                                                "length": {
                                                    "type": "string",
                                                    "enum": ["short", "medium", "long"],
                                                },
                                                "writing_style": {
                                                    "type": "string",
                                                    "enum": [
                                                        "conversational",
                                                        "explanatory",
                                                        "casual",
                                                        "expert",
                                                    ],
                                                },
                                                "language": {
                                                    "type": "string",
                                                    "enum": ["ko", "en", "ja"],
                                                },
                                            },
                                        },
                                        "detail_level": {
                                            "type": "string",
                                            "enum": ["brief", "standard", "deep"],
                                            "default": "standard",
                                        },
                                        "output_format": {
                                            "type": "string",
                                            "enum": ["html", "markdown", "plain"],
                                            "default": "html",
                                        },
                                        "max_chars": {
                                            "type": "integer",
                                            "minimum": 100,
                                            "maximum": 50000,
                                        },
                                        "include_transcript": {
                                            "type": "boolean",
                                            "default": False,
                                        },
                                        "web_search": {
                                            "type": "boolean",
                                            "default": False,
                                        },
                                        "agent_mode": {
                                            "type": "boolean",
                                            "default": False,
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
    }
