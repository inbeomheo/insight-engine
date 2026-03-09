"""브라우저 API 폴백 서비스 테스트"""

import unittest
from services.browser_api_fallback_service import (
    APICapability, CompatibilityReport,
    check_capabilities, suggest_fallback, generate_polyfill_list,
    calculate_compatibility_score,
)


class TestBrowserAPIFallbackService(unittest.TestCase):
    """브라우저 API 폴백 서비스 테스트"""

    def test_check_capabilities_all_supported(self):
        """모든 API 지원"""
        report = check_capabilities(
            ["fetch", "Promise"],
            ["fetch", "Promise", "WebSocket"],
        )
        self.assertEqual(report.supported_count, 2)
        self.assertEqual(report.total_count, 2)
        self.assertEqual(report.score, 1.0)

    def test_check_capabilities_none_supported(self):
        """API 미지원"""
        report = check_capabilities(["WebSocket", "WebRTC"], [])
        self.assertEqual(report.supported_count, 0)
        self.assertEqual(report.score, 0.0)

    def test_check_capabilities_partial(self):
        """일부 지원"""
        report = check_capabilities(
            ["fetch", "WebSocket", "WebRTC"],
            ["fetch"],
        )
        self.assertEqual(report.supported_count, 1)
        self.assertAlmostEqual(report.score, 1 / 3)

    def test_check_capabilities_empty_required(self):
        """빈 필수 목록 → 100%"""
        report = check_capabilities([], ["fetch"])
        self.assertEqual(report.score, 1.0)
        self.assertEqual(report.total_count, 0)

    def test_check_capabilities_fallback_info(self):
        """폴백 정보 포함"""
        report = check_capabilities(["fetch"], [])
        cap = report.capabilities[0]
        self.assertEqual(cap.api_name, "fetch")
        self.assertFalse(cap.supported)
        self.assertEqual(cap.fallback, "XMLHttpRequest")

    def test_check_capabilities_polyfill_info(self):
        """폴리필 정보 포함"""
        report = check_capabilities(["IntersectionObserver"], [])
        cap = report.capabilities[0]
        self.assertTrue(cap.polyfill_available)

    def test_suggest_fallback_known(self):
        """알려진 폴백"""
        self.assertEqual(suggest_fallback("fetch"), "XMLHttpRequest")
        self.assertEqual(suggest_fallback("IndexedDB"), "localStorage")
        self.assertEqual(suggest_fallback("WebSocket"), "long polling")

    def test_suggest_fallback_unknown(self):
        """알 수 없는 API"""
        self.assertIsNone(suggest_fallback("UnknownAPI"))

    def test_generate_polyfill_list(self):
        """필요 폴리필 목록"""
        report = check_capabilities(
            ["IntersectionObserver", "fetch", "WebSocket"],
            [],
        )
        polyfills = generate_polyfill_list(report)
        self.assertIn("IntersectionObserver", polyfills)
        self.assertIn("fetch", polyfills)
        # WebSocket은 폴리필 미가용
        self.assertNotIn("WebSocket", polyfills)

    def test_generate_polyfill_list_all_supported(self):
        """모두 지원 → 빈 폴리필"""
        report = check_capabilities(["fetch"], ["fetch"])
        polyfills = generate_polyfill_list(report)
        self.assertEqual(polyfills, [])

    def test_calculate_compatibility_score(self):
        """호환성 점수 계산"""
        report = check_capabilities(["fetch", "Promise"], ["fetch"])
        score = calculate_compatibility_score(report)
        self.assertEqual(score, 0.5)

    def test_suggest_fallback_multiple(self):
        """여러 API 폴백 확인"""
        apis = ["IntersectionObserver", "WebGL", "Geolocation"]
        for api in apis:
            fb = suggest_fallback(api)
            self.assertIsNotNone(fb, f"{api}에 대한 폴백이 없음")

    def test_check_capabilities_preserves_order(self):
        """입력 순서 유지"""
        required = ["WebSocket", "fetch", "Promise"]
        report = check_capabilities(required, [])
        names = [c.api_name for c in report.capabilities]
        self.assertEqual(names, required)


if __name__ == "__main__":
    unittest.main()
