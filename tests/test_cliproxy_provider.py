import os
import unittest
from unittest.mock import patch

import config
from services.core.ai_service import _build_completion_kwargs, _convert_error_message


class CliProxyProviderTests(unittest.TestCase):
    def setUp(self):
        config._providers_cache = {}
        config._providers_cache_time = 0.0

    def test_cliproxy_provider_exposes_verified_text_models_without_chatmock(self):
        with patch.dict(config.PROVIDER_API_KEYS, {"cliproxy": "test-key", "zai": ""}, clear=False):
            providers = config.get_available_providers()

        self.assertIn("cliproxy", providers)
        self.assertNotIn("chatmock", providers)
        self.assertEqual(providers["cliproxy"]["name"], "OPEN AI")
        self.assertEqual(
            [model["id"] for model in providers["cliproxy"]["models"]],
            [
                "cliproxy/gpt-5.6-sol",
                "cliproxy/gpt-5.6-terra",
                "cliproxy/gpt-5.6-luna",
                "cliproxy/gpt-5.5",
                "cliproxy/gpt-5.4",
                "cliproxy/gpt-5.4-mini",
                "cliproxy/gpt-5.3-codex-spark",
            ],
        )

    def test_cliproxy_is_default_and_legacy_chatmock_model_is_migrated(self):
        self.assertEqual(config.DEPLOYMENT_MODEL, "cliproxy/gpt-5.6-sol")
        self.assertEqual(
            config.coerce_deployment_model("chatmock/gpt-5.3-codex-spark"),
            "cliproxy/gpt-5.3-codex-spark",
        )
        self.assertEqual(
            config.coerce_deployment_model("gpt-5.4-mini"),
            "cliproxy/gpt-5.4-mini",
        )
        self.assertEqual(
            config.coerce_deployment_model("unsupported/model"),
            config.DEPLOYMENT_MODEL,
        )

    def test_completion_uses_cliproxy_openai_endpoint_and_key(self):
        with patch.dict(os.environ, {
            "CLIPROXY_BASE_URL": "http://cli-proxy-api:8317/v1",
            "CLIPROXY_API_KEY": "test-cliproxy-key",
        }):
            kwargs = _build_completion_kwargs(
                "cliproxy/gpt-5.6-sol",
                "테스트 프롬프트",
                style_id="summary",
                modifiers={"length": "short"},
            )

        self.assertEqual(kwargs["model"], "openai/gpt-5.6-sol")
        self.assertEqual(kwargs["api_base"], "http://cli-proxy-api:8317/v1")
        self.assertEqual(kwargs["api_key"], "test-cliproxy-key")
        self.assertEqual(kwargs["reasoning_effort"], "medium")
        self.assertTrue(kwargs["drop_params"])
        self.assertNotIn("temperature", kwargs)

    def test_connection_error_mentions_cliproxy_not_chatmock(self):
        message = _convert_error_message(
            "connection refused",
            "cliproxy/gpt-5.6-sol",
        )

        self.assertIn("CLIProxyAPI 연결 실패", message)
        self.assertNotIn("ChatMock", message)


if __name__ == "__main__":
    unittest.main()
