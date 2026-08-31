"""캐시 fingerprint 분리: 사용자/커스텀 프롬프트/상세도/웹검색."""
import hashlib
import os
import tempfile
import unittest

from services.core.cache_service import AICacheService


class TestCacheFingerprint(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "test_cache.db")
        self.cache = AICacheService(self.db_path, ttl_days=1, max_size_mb=1)

    def test_custom_prompt_is_hashed_not_raw(self):
        key = AICacheService.make_key(
            "vid", "summary", "model", custom_prompt="secret prompt text"
        )
        self.assertNotIn("secret prompt text", key)
        digest = hashlib.sha256(b"secret prompt text").hexdigest()
        # 키 자체는 sha256 hex이며 원문이 들어가면 안 됨
        self.assertEqual(len(key), 64)
        self.assertNotEqual(key, digest)

    def test_cross_user_custom_prompt_separation(self):
        a = AICacheService.make_key(
            "vid", "summary", "model", custom_prompt="p1", user_id="user-a"
        )
        b = AICacheService.make_key(
            "vid", "summary", "model", custom_prompt="p1", user_id="user-b"
        )
        self.assertNotEqual(a, b)

    def test_detail_and_web_search_separation(self):
        brief = AICacheService.make_key("vid", "summary", "model", detail_level="brief")
        deep = AICacheService.make_key("vid", "summary", "model", detail_level="deep")
        no_web = AICacheService.make_key("vid", "summary", "model", web_search=False)
        web = AICacheService.make_key("vid", "summary", "model", web_search=True)
        self.assertNotEqual(brief, deep)
        self.assertNotEqual(no_web, web)

    def test_output_format_and_analyze_separation(self):
        html = AICacheService.make_key("vid", "summary", "model", output_format="html")
        plain = AICacheService.make_key("vid", "summary", "model", output_format="plain")
        analyzed = AICacheService.make_key("vid", "summary", "model", analyze=True)
        self.assertNotEqual(html, plain)
        self.assertNotEqual(html, analyzed)
