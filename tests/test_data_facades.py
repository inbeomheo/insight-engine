"""services/data/ 도메인 facade 스모크 테스트.

PR #20 Codex 지적(P0): auth_routes / usage_service가 import하는 facade 모듈이
실제로 존재하지 않아 앱 부팅이 ModuleNotFoundError로 막혔었다.
본 테스트는 facade 모듈이 존재하고 기대한 심볼을 재노출하며,
재노출된 함수가 원본 구현과 동일 객체인지 검증한다.
"""
import importlib
import unittest


class TestDataFacades(unittest.TestCase):

    def test_api_key_storage_facade_exports(self):
        m = importlib.import_module("services.data.api_key_storage_facade")
        for name in ("save_api_keys", "get_api_keys"):
            self.assertTrue(hasattr(m, name), f"{name} 누락")

    def test_custom_style_facade_exports(self):
        m = importlib.import_module("services.data.custom_style_facade")
        for name in ("save_custom_style", "get_custom_styles", "delete_custom_style"):
            self.assertTrue(hasattr(m, name), f"{name} 누락")

    def test_usage_admin_facade_exports(self):
        m = importlib.import_module("services.data.usage_admin_facade")
        for name in ("get_usage", "decrement_usage", "is_admin",
                     "get_all_users_usage", "reset_user_usage", "get_usage_stats"):
            self.assertTrue(hasattr(m, name), f"{name} 누락")

    def test_content_admin_facade_exports(self):
        m = importlib.import_module("services.data.content_admin_facade")
        for name in ("get_all_contents", "get_content_detail"):
            self.assertTrue(hasattr(m, name), f"{name} 누락")

    def test_account_admin_facade_exports(self):
        m = importlib.import_module("services.data.account_admin_facade")
        for name in ("delete_user_account", "update_user_profile", "update_user_password"):
            self.assertTrue(hasattr(m, name), f"{name} 누락")

    def test_snippet_facade_exports(self):
        m = importlib.import_module("services.data.snippet_facade")
        for name in ("get_user_snippets", "create_snippet", "delete_snippet"):
            self.assertTrue(hasattr(m, name), f"{name} 누락")

    def test_facade_reexports_same_object(self):
        # 재노출은 원본 구현과 동일 객체여야 한다 (얇은 facade).
        from services.data import usage_admin_facade
        from services.data import supabase_service
        from services.data.supabase_admin import admin_queries
        self.assertIs(usage_admin_facade.get_usage, supabase_service.get_usage)
        self.assertIs(usage_admin_facade.is_admin, admin_queries.is_admin)

    def test_auth_routes_imports_resolve(self):
        # facade 누락 시 ModuleNotFoundError가 났던 회귀를 방지.
        importlib.import_module("routes.auth_routes")
        importlib.import_module("services.usage.usage_service")


if __name__ == "__main__":
    unittest.main()
