"""오픈소셜 스타터팩 서비스 테스트"""
import unittest
from services.open_social_starter_service import (
    create_starter_pack, generate_bio, suggest_hashtags, create_content_calendar,
    StarterPack, SocialProfile
)


class TestOpenSocialStarterService(unittest.TestCase):

    def setUp(self):
        self.pack = create_starter_pack('TestBrand', ['twitter', 'instagram'])

    def test_create_starter_pack(self):
        self.assertIsInstance(self.pack, StarterPack)
        self.assertEqual(len(self.pack.profiles), 2)

    def test_starter_pack_handle(self):
        twitter_profile = [p for p in self.pack.profiles if p.platform == 'twitter'][0]
        self.assertEqual(twitter_profile.handle, '@testbrand')

    def test_starter_pack_tips(self):
        self.assertGreater(len(self.pack.tips), 0)

    def test_generate_bio_twitter(self):
        bio = generate_bio('MyBrand', 'twitter')
        self.assertIn('MyBrand', bio)

    def test_generate_bio_linkedin(self):
        bio = generate_bio('MyBrand', 'linkedin')
        self.assertIn('전문적', bio)

    def test_generate_bio_unknown_platform(self):
        bio = generate_bio('MyBrand', 'unknown')
        self.assertIn('MyBrand', bio)

    def test_suggest_hashtags_count(self):
        tags = suggest_hashtags('AI', 'twitter')
        self.assertEqual(len(tags), 3)  # twitter config

    def test_suggest_hashtags_instagram(self):
        tags = suggest_hashtags('AI', 'instagram')
        self.assertEqual(len(tags), 10)

    def test_suggest_hashtags_include_topic(self):
        tags = suggest_hashtags('AI', 'twitter')
        self.assertEqual(tags[0], '#AI')

    def test_create_content_calendar(self):
        calendar = create_content_calendar(self.pack, 3)
        # 3일 * 2 플랫폼 = 6 항목
        self.assertEqual(len(calendar), 6)

    def test_create_content_calendar_fields(self):
        calendar = create_content_calendar(self.pack, 1)
        entry = calendar[0]
        self.assertIn('day', entry)
        self.assertIn('platform', entry)
        self.assertIn('content_type', entry)

    def test_starter_pack_schedule(self):
        twitter_profile = [p for p in self.pack.profiles if p.platform == 'twitter'][0]
        self.assertGreater(len(twitter_profile.posting_schedule), 0)


if __name__ == '__main__':
    unittest.main()
