"""Deployment provider policy tests.

The local Insight Engine deployment intentionally exposes only the ChatMock-backed
provider, branded as OPEN AI, even when other provider credentials exist in the
environment.
"""
from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch


class TestDeploymentProviderPolicy(unittest.TestCase):
    def test_only_open_ai_chatmock_provider_is_exposed(self):
        with patch.dict(
            os.environ,
            {
                "CHATMOCK_API_KEY": "dummy",
                "DEEPSEEK_API_KEY": "should-not-expose",
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "ZHIPUAI_API_KEY": "should-not-expose",
                "TRANSLATION_MODEL": "gemini/should-not-use",
                "AGENT_DEFAULT_MODEL": "ollama/should-not-use",
            },
            clear=False,
        ):
            import config

            config = importlib.reload(config)
            providers = config.get_available_providers()

        self.assertEqual(list(providers.keys()), ["chatmock"])
        self.assertEqual(providers["chatmock"]["name"], "OPEN AI")
        self.assertEqual(
            [m["id"] for m in providers["chatmock"]["models"]],
            ["chatmock/gpt-5.3-codex-spark"],
        )
        self.assertEqual(config.FALLBACK_CHAIN, ["chatmock/gpt-5.3-codex-spark"])
        self.assertEqual(config.MAX_FALLBACK_ATTEMPTS, 1)
        self.assertEqual(config.TRANSLATION_MODEL, "chatmock/gpt-5.3-codex-spark")

    def test_all_model_inputs_are_coerced_to_deployment_model(self):
        import config

        self.assertEqual(
            config.coerce_deployment_model("gemini/gemini-3.1-pro-preview"),
            "chatmock/gpt-5.3-codex-spark",
        )
        self.assertEqual(
            config.coerce_deployment_model("gpt-5.4-mini"),
            "chatmock/gpt-5.3-codex-spark",
        )


if __name__ == "__main__":
    unittest.main()
