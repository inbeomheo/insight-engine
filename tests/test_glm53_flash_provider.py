import os
import unittest
from unittest.mock import patch

import config
from services.core.ai_service import _build_completion_kwargs


class Glm53FlashProviderTests(unittest.TestCase):
    def setUp(self):
        config._providers_cache = {}
        config._providers_cache_time = 0.0

    def test_zai_provider_exposes_glm_53_flash(self):
        with patch.dict(os.environ, {"ZAI_API_KEY": "test-zai-key"}):
            with patch.dict(config.PROVIDER_API_KEYS, {"zai": "test-zai-key"}, clear=False):
                providers = config.get_available_providers()

        self.assertIn("zai", providers)
        models = providers["zai"]["models"]
        self.assertIn(
            {"id": "zai/glm-5.3-flash", "name": "GLM-5.3 Flash", "max_input_tokens": 1_000_000,
             "price_input": 0.15, "price_output": 0.50},
            models,
        )

    def test_selected_glm_model_is_not_coerced_to_chatmock(self):
        self.assertEqual(
            config.coerce_deployment_model("zai/glm-5.3-flash"),
            "zai/glm-5.3-flash",
        )
        self.assertEqual(
            config.coerce_deployment_model("unsupported/provider-model"),
            config.DEPLOYMENT_MODEL,
        )

    def test_glm_completion_uses_zai_endpoint_and_key(self):
        with patch.dict(os.environ, {
            "ZAI_API_KEY": "test-zai-key",
            "ZHIPUAI_API_BASE": "https://api.z.ai/api/coding/paas/v4",
        }):
            kwargs = _build_completion_kwargs(
                "zai/glm-5.3-flash",
                "테스트 프롬프트",
                style_id="summary",
                modifiers={"length": "short"},
            )

        self.assertEqual(kwargs["model"], "zai/glm-5.3-flash")
        self.assertEqual(kwargs["api_key"], "test-zai-key")
        self.assertEqual(kwargs["api_base"], "https://api.z.ai/api/coding/paas/v4")
        self.assertEqual(kwargs["reasoning_effort"], "max")


if __name__ == "__main__":
    unittest.main()
