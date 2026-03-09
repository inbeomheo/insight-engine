"""프라이빗 PWA 서비스 테스트."""

import unittest
from services.private_pwa_service import (
    PWAConfig,
    generate_manifest,
    generate_sw_config,
    validate_config,
    generate_install_prompt,
)


class TestPrivatePWAService(unittest.TestCase):
    """PrivatePWAService 단위 테스트."""

    def _make_valid_config(self) -> PWAConfig:
        return PWAConfig(
            app_name="Insight Engine",
            short_name="IE",
            theme_color="#1A1612",
            background_color="#FFFFFF",
            display="standalone",
            start_url="/",
            icons=[{"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"}],
            scope="/",
        )

    def test_generate_manifest_basic(self):
        """기본 매니페스트를 올바르게 생성한다."""
        config = self._make_valid_config()
        manifest = generate_manifest(config)
        self.assertEqual(manifest["name"], "Insight Engine")
        self.assertEqual(manifest["short_name"], "IE")
        self.assertEqual(manifest["display"], "standalone")
        self.assertEqual(manifest["start_url"], "/")

    def test_generate_manifest_includes_icons(self):
        """매니페스트에 아이콘이 포함된다."""
        config = self._make_valid_config()
        manifest = generate_manifest(config)
        self.assertEqual(len(manifest["icons"]), 1)
        self.assertEqual(manifest["icons"][0]["sizes"], "192x192")

    def test_generate_manifest_colors(self):
        """매니페스트에 색상이 포함된다."""
        config = self._make_valid_config()
        manifest = generate_manifest(config)
        self.assertEqual(manifest["theme_color"], "#1A1612")
        self.assertEqual(manifest["background_color"], "#FFFFFF")

    def test_generate_sw_config_cache_first(self):
        """cache-first 전략 서비스워커 설정."""
        sw = generate_sw_config("cache-first", ["/", "/api/health"])
        self.assertEqual(sw["cache_strategy"], "cache-first")
        self.assertIn("/", sw["routes"])
        self.assertIn("cache_name", sw)

    def test_generate_sw_config_network_first(self):
        """network-first 전략 서비스워커 설정."""
        sw = generate_sw_config("network-first", ["/api/data"])
        self.assertEqual(sw["cache_strategy"], "network-first")

    def test_generate_sw_config_stale_while_revalidate(self):
        """stale-while-revalidate 전략."""
        sw = generate_sw_config("stale-while-revalidate", ["/assets"])
        self.assertEqual(sw["cache_strategy"], "stale-while-revalidate")

    def test_generate_sw_config_invalid_strategy(self):
        """유효하지 않은 전략은 network-first로 폴백."""
        sw = generate_sw_config("invalid", ["/"])
        self.assertEqual(sw["cache_strategy"], "network-first")

    def test_validate_config_valid(self):
        """유효한 설정은 빈 오류 목록."""
        config = self._make_valid_config()
        errors = validate_config(config)
        self.assertEqual(errors, [])

    def test_validate_config_missing_name(self):
        """app_name이 빈 문자열이면 오류."""
        config = self._make_valid_config()
        config.app_name = ""
        errors = validate_config(config)
        self.assertTrue(any("app_name" in e for e in errors))

    def test_validate_config_invalid_color(self):
        """색상 형식이 올바르지 않으면 오류."""
        config = self._make_valid_config()
        config.theme_color = "not-a-color"
        errors = validate_config(config)
        self.assertTrue(any("theme_color" in e for e in errors))

    def test_validate_config_invalid_display(self):
        """유효하지 않은 display 모드면 오류."""
        config = self._make_valid_config()
        config.display = "popup"
        errors = validate_config(config)
        self.assertTrue(any("display" in e for e in errors))

    def test_validate_config_no_icons(self):
        """아이콘이 없으면 오류."""
        config = self._make_valid_config()
        config.icons = []
        errors = validate_config(config)
        self.assertTrue(any("아이콘" in e for e in errors))

    def test_validate_config_icon_missing_src(self):
        """아이콘에 src가 없으면 오류."""
        config = self._make_valid_config()
        config.icons = [{"sizes": "192x192"}]
        errors = validate_config(config)
        self.assertTrue(any("src" in e for e in errors))

    def test_validate_config_short_hex(self):
        """3자리 16진 색상도 유효."""
        config = self._make_valid_config()
        config.theme_color = "#FFF"
        errors = validate_config(config)
        self.assertFalse(any("theme_color" in e for e in errors))

    def test_generate_install_prompt(self):
        """설치 프롬프트 메타데이터 생성."""
        config = self._make_valid_config()
        prompt = generate_install_prompt(config)
        self.assertEqual(prompt["app_name"], "Insight Engine")
        self.assertEqual(prompt["install_button_text"], "설치")
        self.assertIsNotNone(prompt["icon"])

    def test_generate_install_prompt_no_icons(self):
        """아이콘 없는 설정의 설치 프롬프트."""
        config = self._make_valid_config()
        config.icons = []
        prompt = generate_install_prompt(config)
        self.assertIsNone(prompt["icon"])


if __name__ == "__main__":
    unittest.main()
