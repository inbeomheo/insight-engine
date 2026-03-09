"""AI 크롤링 게이트웨이 서비스 테스트"""

import unittest
from services.ai_crawl_gateway_service import (
    CrawlRule, CrawlDecision,
    evaluate_request, generate_robots_txt, check_rate_limit, get_bot_stats,
)


class TestAICrawlGatewayService(unittest.TestCase):
    """AI 크롤링 게이트웨이 서비스 테스트"""

    def _make_rule(self, bot="Googlebot", allowed=None, blocked=None, rate=60):
        return CrawlRule(
            rule_id="r1",
            bot_name=bot,
            allowed_paths=allowed or ["/public/*"],
            blocked_paths=blocked or ["/admin/*"],
            rate_limit=rate,
        )

    def test_evaluate_allowed(self):
        """허용 경로 매칭"""
        rules = [self._make_rule(allowed=["/public/*"])]
        decision = evaluate_request("Googlebot", "/public/page", rules)
        self.assertTrue(decision.allowed)

    def test_evaluate_blocked(self):
        """차단 경로 매칭"""
        rules = [self._make_rule(blocked=["/admin/*"])]
        decision = evaluate_request("Googlebot", "/admin/settings", rules)
        self.assertFalse(decision.allowed)

    def test_evaluate_blocked_priority(self):
        """차단이 허용보다 우선"""
        rules = [self._make_rule(allowed=["/*"], blocked=["/admin/*"])]
        decision = evaluate_request("Googlebot", "/admin/page", rules)
        self.assertFalse(decision.allowed)

    def test_evaluate_no_rules(self):
        """규칙 없으면 기본 거부"""
        decision = evaluate_request("UnknownBot", "/page", [])
        self.assertFalse(decision.allowed)

    def test_evaluate_wildcard_bot(self):
        """와일드카드 봇 매칭"""
        rules = [self._make_rule(bot="*", allowed=["/public/*"])]
        decision = evaluate_request("AnyBot", "/public/page", rules)
        self.assertTrue(decision.allowed)

    def test_evaluate_no_match(self):
        """허용 경로에 매칭 안 됨"""
        rules = [self._make_rule(allowed=["/api/*"])]
        decision = evaluate_request("Googlebot", "/other/page", rules)
        self.assertFalse(decision.allowed)

    def test_generate_robots_txt(self):
        """robots.txt 생성"""
        rules = [self._make_rule(bot="GPTBot", allowed=["/blog/*"], blocked=["/internal/*"], rate=10)]
        txt = generate_robots_txt(rules)
        self.assertIn("User-agent: GPTBot", txt)
        self.assertIn("Allow: /blog/*", txt)
        self.assertIn("Disallow: /internal/*", txt)
        self.assertIn("Crawl-delay:", txt)

    def test_generate_robots_txt_multiple(self):
        """여러 규칙"""
        rules = [
            self._make_rule(bot="Bot1", allowed=["/a"]),
            self._make_rule(bot="Bot2", allowed=["/b"]),
        ]
        txt = generate_robots_txt(rules)
        self.assertIn("Bot1", txt)
        self.assertIn("Bot2", txt)

    def test_check_rate_limit_within(self):
        """속도 제한 이내"""
        rules = [self._make_rule(rate=100)]
        self.assertTrue(check_rate_limit("Googlebot", 50, rules))

    def test_check_rate_limit_exceeded(self):
        """속도 제한 초과"""
        rules = [self._make_rule(rate=10)]
        self.assertFalse(check_rate_limit("Googlebot", 11, rules))

    def test_check_rate_limit_no_rule(self):
        """규칙 없으면 기본 거부"""
        self.assertFalse(check_rate_limit("Unknown", 1, []))

    def test_get_bot_stats(self):
        """봇별 통계"""
        decisions = [
            CrawlDecision("BotA", "/p1", True, "ok"),
            CrawlDecision("BotA", "/p2", False, "blocked"),
            CrawlDecision("BotB", "/p1", True, "ok"),
        ]
        stats = get_bot_stats(decisions)
        self.assertEqual(stats["BotA"]["total"], 2)
        self.assertEqual(stats["BotA"]["allowed"], 1)
        self.assertEqual(stats["BotA"]["blocked"], 1)
        self.assertEqual(stats["BotB"]["total"], 1)

    def test_get_bot_stats_empty(self):
        """빈 결정 목록"""
        self.assertEqual(get_bot_stats([]), {})

    def test_check_rate_limit_exact(self):
        """정확히 제한에 도달"""
        rules = [self._make_rule(rate=10)]
        self.assertTrue(check_rate_limit("Googlebot", 10, rules))


if __name__ == "__main__":
    unittest.main()
