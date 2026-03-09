"""channel_fork_service 단위 테스트

채널별 분기 생성 + 숏폼 리퍼포징의 순수 Python 로직을 검증한다.
"""
import unittest

from services.channel_fork_service import (
    ChannelConfig,
    ChannelPost,
    RepurposePack,
    fork_for_channels,
    repurpose_longform,
    _extract_sentences,
    _extract_keywords,
    _adjust_tone,
    _truncate,
    _build_thread,
    _build_card_news,
    _build_email_teaser,
    _build_summary,
    DEFAULT_CHANNELS,
)


# ── 샘플 콘텐츠 ──────────────────────────────────────────────

SAMPLE_CONTENT = (
    "인공지능 기술이 빠르게 발전합니다. "
    "자연어 처리 분야에서 대규모 언어 모델이 주목받고 있습니다. "
    "기업들은 생산성 향상을 위해 AI를 도입합니다. "
    "하지만 윤리적 문제도 함께 논의되어야 합니다. "
    "데이터 프라이버시와 편향성 해소가 중요한 과제입니다. "
    "앞으로 AI와 인간의 협업이 더욱 중요해질 것입니다."
)

LONG_CONTENT = SAMPLE_CONTENT * 10  # 반복으로 장문 생성


class TestChannelConfig(unittest.TestCase):
    """ChannelConfig 데이터 클래스 테스트"""

    def test_default_hashtag_count(self):
        """hashtag_count 기본값은 0"""
        config = ChannelConfig(name="test", max_length=100, tone="casual")
        self.assertEqual(config.hashtag_count, 0)

    def test_custom_hashtag_count(self):
        """hashtag_count 커스텀 값"""
        config = ChannelConfig(name="instagram", max_length=2200, tone="friendly", hashtag_count=10)
        self.assertEqual(config.hashtag_count, 10)

    def test_default_channels_preset(self):
        """기본 채널 프리셋 5개 존재"""
        self.assertEqual(len(DEFAULT_CHANNELS), 5)
        self.assertIn("twitter", DEFAULT_CHANNELS)
        self.assertIn("linkedin", DEFAULT_CHANNELS)
        self.assertIn("instagram", DEFAULT_CHANNELS)
        self.assertIn("blog", DEFAULT_CHANNELS)
        self.assertIn("newsletter", DEFAULT_CHANNELS)


class TestExtractSentences(unittest.TestCase):
    """문장 분리 헬퍼 테스트"""

    def test_basic_split(self):
        """마침표 기준 문장 분리"""
        sentences = _extract_sentences("첫 문장입니다. 두 번째 문장입니다.")
        self.assertEqual(len(sentences), 2)

    def test_empty_input(self):
        """빈 입력 → 빈 리스트"""
        self.assertEqual(_extract_sentences(""), [])
        self.assertEqual(_extract_sentences("   "), [])

    def test_markdown_header_removed(self):
        """마크다운 헤더(#) 제거"""
        sentences = _extract_sentences("## 제목입니다. 본문입니다.")
        # '#' 마커가 제거되어야 함
        self.assertTrue(all(not s.startswith('#') for s in sentences))

    def test_markdown_list_removed(self):
        """마크다운 리스트(- *) 제거"""
        text = "- 항목 하나입니다. * 항목 둘입니다."
        sentences = _extract_sentences(text)
        self.assertTrue(all(not s.startswith('-') and not s.startswith('*') for s in sentences))

    def test_question_mark_split(self):
        """물음표로 문장 분리"""
        sentences = _extract_sentences("왜 그럴까요? 이유는 간단합니다.")
        self.assertEqual(len(sentences), 2)


class TestExtractKeywords(unittest.TestCase):
    """키워드 추출 헬퍼 테스트"""

    def test_count_limit(self):
        """요청 개수만큼 키워드 반환"""
        keywords = _extract_keywords(SAMPLE_CONTENT, 3)
        self.assertEqual(len(keywords), 3)

    def test_zero_count(self):
        """0개 요청 → 빈 리스트"""
        self.assertEqual(_extract_keywords(SAMPLE_CONTENT, 0), [])

    def test_stopwords_excluded(self):
        """불용어(그리고, 하지만 등)가 결과에 포함되지 않음"""
        text = "그리고 하지만 인공지능 인공지능 인공지능"
        keywords = _extract_keywords(text, 5)
        self.assertNotIn("그리고", keywords)
        self.assertNotIn("하지만", keywords)


class TestAdjustTone(unittest.TestCase):
    """톤 조정 헬퍼 테스트"""

    def test_casual_tone(self):
        """casual: ~합니다 → ~함"""
        result = _adjust_tone("기술이 발전합니다", "casual")
        self.assertIn("함", result)
        self.assertNotIn("합니다", result)

    def test_friendly_tone(self):
        """friendly: ~합니다 → ~해요"""
        result = _adjust_tone("기술이 발전합니다", "friendly")
        self.assertIn("해요", result)
        self.assertNotIn("합니다", result)

    def test_professional_tone(self):
        """professional: 원본 유지"""
        original = "기술이 발전합니다"
        result = _adjust_tone(original, "professional")
        self.assertEqual(result, original)


class TestTruncate(unittest.TestCase):
    """글자수 자르기 헬퍼 테스트"""

    def test_within_limit(self):
        """제한 이내 → 원본 그대로"""
        text = "짧은 텍스트"
        self.assertEqual(_truncate(text, 100), text)

    def test_exceeds_limit(self):
        """제한 초과 → 말줄임표 포함"""
        result = _truncate(LONG_CONTENT, 100)
        self.assertLessEqual(len(result), 100)
        self.assertTrue(result.endswith("..."))

    def test_sentence_boundary(self):
        """문장 경계에서 자르기"""
        text = "첫 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
        result = _truncate(text, 30)
        self.assertLessEqual(len(result), 30)


class TestForkForChannels(unittest.TestCase):
    """fork_for_channels 핵심 기능 테스트"""

    def test_single_channel(self):
        """단일 채널 분기"""
        channels = [{"name": "twitter", "max_length": 280, "tone": "casual", "hashtag_count": 3}]
        results = fork_for_channels(SAMPLE_CONTENT, channels)
        self.assertIn("twitter", results)
        self.assertIsInstance(results["twitter"], ChannelPost)

    def test_multiple_channels(self):
        """복수 채널 동시 분기"""
        channels = [
            {"name": "twitter", "max_length": 280, "tone": "casual", "hashtag_count": 3},
            {"name": "linkedin", "max_length": 1300, "tone": "professional", "hashtag_count": 5},
            {"name": "instagram", "max_length": 2200, "tone": "friendly", "hashtag_count": 10},
        ]
        results = fork_for_channels(SAMPLE_CONTENT, channels)
        self.assertEqual(len(results), 3)
        for name in ["twitter", "linkedin", "instagram"]:
            self.assertIn(name, results)

    def test_max_length_respected(self):
        """채널별 max_length가 지켜지는지 확인"""
        channels = [
            {"name": "twitter", "max_length": 280, "tone": "casual", "hashtag_count": 0},
            {"name": "blog", "max_length": 5000, "tone": "professional", "hashtag_count": 0},
        ]
        results = fork_for_channels(LONG_CONTENT, channels)
        self.assertLessEqual(results["twitter"].char_count, 280)
        self.assertLessEqual(results["blog"].char_count, 5000)

    def test_tone_difference(self):
        """채널별 톤 차이가 콘텐츠에 반영됨"""
        channels = [
            {"name": "casual_ch", "max_length": 5000, "tone": "casual", "hashtag_count": 0},
            {"name": "formal_ch", "max_length": 5000, "tone": "professional", "hashtag_count": 0},
        ]
        results = fork_for_channels(SAMPLE_CONTENT, channels)
        # casual에는 '함'이 있고 professional에는 '합니다'가 있어야 함
        self.assertIn("함", results["casual_ch"].content)
        self.assertIn("합니다", results["formal_ch"].content)

    def test_hashtags_included(self):
        """해시태그가 요청 개수만큼 포함됨"""
        channels = [{"name": "instagram", "max_length": 2200, "tone": "friendly", "hashtag_count": 5}]
        results = fork_for_channels(SAMPLE_CONTENT, channels)
        post = results["instagram"]
        self.assertEqual(len(post.hashtags), 5)
        # 콘텐츠에 # 기호가 포함됨
        self.assertIn("#", post.content)

    def test_no_hashtags_when_zero(self):
        """hashtag_count=0이면 해시태그 없음"""
        channels = [{"name": "blog", "max_length": 5000, "tone": "professional", "hashtag_count": 0}]
        results = fork_for_channels(SAMPLE_CONTENT, channels)
        self.assertEqual(results["blog"].hashtags, [])

    def test_word_count_positive(self):
        """word_count가 양수"""
        channels = [{"name": "twitter", "max_length": 280, "tone": "casual"}]
        results = fork_for_channels(SAMPLE_CONTENT, channels)
        self.assertGreater(results["twitter"].word_count, 0)

    def test_empty_content_raises(self):
        """빈 콘텐츠 → ValueError"""
        channels = [{"name": "twitter", "max_length": 280, "tone": "casual"}]
        with self.assertRaises(ValueError):
            fork_for_channels("", channels)
        with self.assertRaises(ValueError):
            fork_for_channels("   ", channels)

    def test_empty_channels_raises(self):
        """빈 채널 목록 → ValueError"""
        with self.assertRaises(ValueError):
            fork_for_channels(SAMPLE_CONTENT, [])

    def test_char_count_matches(self):
        """char_count가 실제 content 길이와 일치"""
        channels = [{"name": "twitter", "max_length": 280, "tone": "casual", "hashtag_count": 2}]
        results = fork_for_channels(SAMPLE_CONTENT, channels)
        post = results["twitter"]
        self.assertEqual(post.char_count, len(post.content))


class TestRepurposeLongform(unittest.TestCase):
    """repurpose_longform 핵심 기능 테스트"""

    def test_returns_repurpose_pack(self):
        """RepurposePack 타입 반환"""
        result = repurpose_longform(SAMPLE_CONTENT)
        self.assertIsInstance(result, RepurposePack)

    def test_thread_is_list(self):
        """thread는 비어있지 않은 리스트"""
        result = repurpose_longform(SAMPLE_CONTENT)
        self.assertIsInstance(result.thread, list)
        self.assertGreater(len(result.thread), 0)

    def test_thread_280_char_limit(self):
        """각 트윗이 280자 이내"""
        result = repurpose_longform(LONG_CONTENT)
        for tweet in result.thread:
            self.assertLessEqual(len(tweet), 280)

    def test_card_news_structure(self):
        """card_news: [{title, body}] 구조"""
        result = repurpose_longform(SAMPLE_CONTENT)
        self.assertIsInstance(result.card_news, list)
        self.assertGreater(len(result.card_news), 0)
        for slide in result.card_news:
            self.assertIn("title", slide)
            self.assertIn("body", slide)

    def test_card_news_count_range(self):
        """카드뉴스 슬라이드 1~7장"""
        result = repurpose_longform(LONG_CONTENT)
        self.assertGreaterEqual(len(result.card_news), 1)
        self.assertLessEqual(len(result.card_news), 7)

    def test_email_teaser_contains_cta(self):
        """이메일 티저에 CTA 문구 포함"""
        result = repurpose_longform(SAMPLE_CONTENT)
        self.assertIn("확인해보세요", result.email_teaser)

    def test_summary_is_string(self):
        """한줄 요약은 비어있지 않은 문자열"""
        result = repurpose_longform(SAMPLE_CONTENT)
        self.assertIsInstance(result.summary, str)
        self.assertGreater(len(result.summary), 0)

    def test_summary_max_100_chars(self):
        """한줄 요약 100자 이내"""
        result = repurpose_longform(SAMPLE_CONTENT)
        self.assertLessEqual(len(result.summary), 100)

    def test_three_plus_formats(self):
        """3포맷 이상 생성됨 (thread + card_news + email_teaser + summary)"""
        result = repurpose_longform(SAMPLE_CONTENT)
        format_count = 0
        if result.thread:
            format_count += 1
        if result.card_news:
            format_count += 1
        if result.email_teaser:
            format_count += 1
        if result.summary:
            format_count += 1
        self.assertGreaterEqual(format_count, 3)

    def test_empty_content_raises(self):
        """빈 콘텐츠 → ValueError"""
        with self.assertRaises(ValueError):
            repurpose_longform("")
        with self.assertRaises(ValueError):
            repurpose_longform("   ")

    def test_short_content(self):
        """짧은 콘텐츠도 정상 동작"""
        result = repurpose_longform("짧은 문장입니다.")
        self.assertIsInstance(result, RepurposePack)
        self.assertGreater(len(result.thread), 0)


class TestBuildThread(unittest.TestCase):
    """트위터 스레드 빌더 테스트"""

    def test_single_sentence_fits(self):
        """한 문장이 280자 이내면 트윗 1개"""
        tweets = _build_thread(["짧은 문장입니다."])
        self.assertEqual(len(tweets), 1)

    def test_long_sentence_split(self):
        """280자 초과 문장 → 강제 분할"""
        long_sentence = "가" * 300
        tweets = _build_thread([long_sentence])
        self.assertGreater(len(tweets), 1)
        for tweet in tweets:
            self.assertLessEqual(len(tweet), 280)


class TestBuildEmailTeaser(unittest.TestCase):
    """이메일 티저 빌더 테스트"""

    def test_teaser_length(self):
        """티저 본문부(CTA 제외)가 과도하게 길지 않음"""
        sentences = _extract_sentences(LONG_CONTENT)
        teaser = _build_email_teaser(sentences)
        # CTA 포함 전체 길이 체크 (200 + CTA 약 25자)
        self.assertLessEqual(len(teaser), 250)


if __name__ == '__main__':
    unittest.main()
