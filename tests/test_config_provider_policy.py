"""Deployment provider policy tests.

The local deployment exposes only the CLIProxyAPI-backed OPEN AI provider and
the directly configured Z.AI provider. Unrelated credentials must never make
additional providers appear in the UI.
"""
from __future__ import annotations

import importlib
import os
import unittest
from unittest.mock import patch


class TestDeploymentProviderPolicy(unittest.TestCase):
    def test_only_approved_cliproxy_and_zai_providers_are_exposed(self):
        with patch.dict(
            os.environ,
            {
                "CLIPROXY_API_KEY": "test-cliproxy-key",
                "ZAI_API_KEY": "test-zai-key",
                "DEEPSEEK_API_KEY": "should-not-expose",
                "OLLAMA_BASE_URL": "http://localhost:11434",
                "TRANSLATION_MODEL": "gemini/should-not-use",
                "AGENT_DEFAULT_MODEL": "ollama/should-not-use",
            },
            clear=False,
        ):
            import config

            config = importlib.reload(config)
            providers = config.get_available_providers()

        self.assertEqual(list(providers.keys()), ["cliproxy", "zai"])
        self.assertEqual(providers["cliproxy"]["name"], "OPEN AI")
        self.assertEqual(providers["zai"]["name"], "Z.AI")
        self.assertEqual(
            providers["cliproxy"]["models"][0]["id"],
            "cliproxy/gpt-5.6-sol",
        )
        self.assertNotIn("chatmock", providers)
        self.assertEqual(config.FALLBACK_CHAIN, ["cliproxy/gpt-5.6-sol"])
        self.assertEqual(config.MAX_FALLBACK_ATTEMPTS, 1)
        self.assertEqual(config.TRANSLATION_MODEL, "cliproxy/gpt-5.6-sol")

    def test_unknown_models_fall_back_but_verified_gpt_models_are_prefixed(self):
        import config

        self.assertEqual(
            config.coerce_deployment_model("gemini/gemini-3.1-pro-preview"),
            "cliproxy/gpt-5.6-sol",
        )
        self.assertEqual(
            config.coerce_deployment_model("gpt-5.4-mini"),
            "cliproxy/gpt-5.4-mini",
        )


if __name__ == "__main__":
    unittest.main()
