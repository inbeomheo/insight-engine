"""
SERP 브리프 + 리서치 브리프 서비스 테스트

generate_serp_brief, generate_research_brief 함수의
규칙 기반 로직을 검증합니다.
"""
import unittest
from services.serp_brief_service import (
    generate_serp_brief,
    generate_research_brief,
    SerpBrief,
    ResearchBrief,
    _classify_difficulty,
    _generate_paa_questions,
    _determine_target_audience,
)


class TestGenerateSerpBrief(unittest.TestCase):
    """generate_serp_brief 함수 테스트"""

    def test_returns_serp_brief_dataclass(self):
        """SerpBrief 데이터클래스를 반환해야 함"""
        result = generate_serp_brief('파이썬 웹 개발')
        self.assertIsInstance(result, SerpBrief)

    def test_keyword_preserved(self):
        """입력 키워드가 그대로 보존되어야 함"""
        result = generate_serp_brief('React 튜토리얼')
        self.assertEqual(result.keyword, 'React 튜토리얼')

    def test_keyword_stripped(self):
        """키워드 앞뒤 공백이 제거되어야 함"""
        result = generate_serp_brief('  Django REST  ')
        self.assertEqual(result.keyword, 'Django REST')

    def test_empty_keyword_raises(self):
        """빈 키워드는 ValueError를 발생시켜야 함"""
        with self.assertRaises(ValueError):
            generate_serp_brief('')

    def test_whitespace_keyword_raises(self):
        """공백만 있는 키워드는 ValueError를 발생시켜야 함"""
        with self.assertRaises(ValueError):
            generate_serp_brief('   ')

    def test_none_keyword_raises(self):
        """None 키워드는 ValueError를 발생시켜야 함"""
        with self.assertRaises(ValueError):
            generate_serp_brief(None)

    def test_paa_questions_minimum_three(self):
        """PAA 질문이 최소 3개 이상이어야 함"""
        result = generate_serp_brief('머신러닝')
        self.assertGreaterEqual(len(result.paa_questions), 3)

    def test_paa_questions_contain_keyword(self):
        """PAA 질문에 키워드가 포함되어야 함"""
        keyword = '블록체인'
        result = generate_serp_brief(keyword)
        for q in result.paa_questions:
            self.assertIn(keyword, q)

    def test_competitor_pages_not_empty(self):
        """경쟁 페이지 목록이 비어있지 않아야 함"""
        result = generate_serp_brief('SEO 최적화')
        self.assertGreater(len(result.competitor_pages), 0)

    def test_competitor_pages_have_required_fields(self):
        """경쟁 페이지에 url, title, word_count 필드가 있어야 함"""
        result = generate_serp_brief('콘텐츠 마케팅')
        for page in result.competitor_pages:
            self.assertIn('url', page)
            self.assertIn('title', page)
            self.assertIn('word_count', page)
            self.assertIsInstance(page['word_count'], int)

    def test_recommended_length_positive(self):
        """권장 글 길이가 양수여야 함"""
        result = generate_serp_brief('데이터 분석')
        self.assertGreater(result.recommended_length, 0)

    def test_recommended_length_within_range(self):
        """권장 글 길이가 800~6000 범위 내여야 함"""
        result = generate_serp_brief('인공지능 트렌드')
        self.assertGreaterEqual(result.recommended_length, 800)
        self.assertLessEqual(result.recommended_length, 6000)

    def test_content_gaps_not_empty(self):
        """콘텐츠 갭이 비어있지 않아야 함"""
        result = generate_serp_brief('UX 디자인')
        self.assertGreater(len(result.content_gaps), 0)

    def test_content_gaps_contain_keyword(self):
        """콘텐츠 갭에 키워드가 포함되어야 함"""
        keyword = '클라우드 컴퓨팅'
        result = generate_serp_brief(keyword)
        for gap in result.content_gaps:
            self.assertIn(keyword, gap)

    def test_difficulty_valid_value(self):
        """난이도가 easy/medium/hard 중 하나여야 함"""
        result = generate_serp_brief('파이썬 기초')
        self.assertIn(result.difficulty, ['easy', 'medium', 'hard'])

    def test_deterministic_output(self):
        """동일 키워드에 대해 동일한 결과를 반환해야 함"""
        result1 = generate_serp_brief('Next.js 가이드')
        result2 = generate_serp_brief('Next.js 가이드')
        self.assertEqual(result1.paa_questions, result2.paa_questions)
        self.assertEqual(result1.difficulty, result2.difficulty)
        self.assertEqual(result1.recommended_length, result2.recommended_length)


class TestClassifyDifficulty(unittest.TestCase):
    """난이도 분류 로직 테스트"""

    def test_hard_keyword_insurance(self):
        """보험 키워드는 hard여야 함"""
        self.assertEqual(_classify_difficulty('자동차 보험 비교'), 'hard')

    def test_hard_keyword_investment(self):
        """투자 키워드는 hard여야 함"""
        self.assertEqual(_classify_difficulty('주식 투자 방법'), 'hard')

    def test_easy_keyword_review(self):
        """후기 키워드는 easy여야 함"""
        self.assertEqual(_classify_difficulty('맛집 후기'), 'easy')

    def test_easy_keyword_recipe(self):
        """레시피 키워드는 easy여야 함"""
        self.assertEqual(_classify_difficulty('김치찌개 레시피'), 'easy')

    def test_easy_long_tail_keyword(self):
        """4단어 이상 롱테일 키워드는 easy여야 함"""
        self.assertEqual(_classify_difficulty('서울 강남 카페 추천 조용한'), 'easy')

    def test_hard_single_word(self):
        """1단어 키워드는 hard여야 함"""
        self.assertEqual(_classify_difficulty('마케팅'), 'hard')

    def test_medium_neutral_keyword(self):
        """중립 2-3단어 키워드는 medium이어야 함"""
        self.assertEqual(_classify_difficulty('파이썬 기초'), 'medium')


class TestGeneratePaaQuestions(unittest.TestCase):
    """PAA 질문 생성 테스트"""

    def test_minimum_three_questions(self):
        """최소 3개 질문 생성"""
        questions = _generate_paa_questions('타입스크립트')
        self.assertGreaterEqual(len(questions), 3)

    def test_questions_are_strings(self):
        """질문이 모두 문자열이어야 함"""
        questions = _generate_paa_questions('도커')
        for q in questions:
            self.assertIsInstance(q, str)
            self.assertGreater(len(q), 0)


class TestGenerateResearchBrief(unittest.TestCase):
    """generate_research_brief 함수 테스트"""

    def test_returns_research_brief_dataclass(self):
        """ResearchBrief 데이터클래스를 반환해야 함"""
        result = generate_research_brief('인공지능 윤리')
        self.assertIsInstance(result, ResearchBrief)

    def test_topic_preserved(self):
        """입력 주제가 보존되어야 함"""
        result = generate_research_brief('생성형 AI')
        self.assertEqual(result.topic, '생성형 AI')

    def test_topic_stripped(self):
        """주제 앞뒤 공백이 제거되어야 함"""
        result = generate_research_brief('  LLM 활용  ')
        self.assertEqual(result.topic, 'LLM 활용')

    def test_empty_topic_raises(self):
        """빈 주제는 ValueError를 발생시켜야 함"""
        with self.assertRaises(ValueError):
            generate_research_brief('')

    def test_none_topic_raises(self):
        """None 주제는 ValueError를 발생시켜야 함"""
        with self.assertRaises(ValueError):
            generate_research_brief(None)

    def test_angles_minimum_three(self):
        """각도가 최소 3개 이상이어야 함"""
        result = generate_research_brief('양자 컴퓨팅')
        self.assertGreaterEqual(len(result.angles), 3)

    def test_angles_contain_topic(self):
        """각도에 주제가 포함되어야 함"""
        topic = '메타버스'
        result = generate_research_brief(topic)
        for angle in result.angles:
            self.assertIn(topic, angle)

    def test_key_questions_minimum_five(self):
        """핵심 질문이 최소 5개 이상이어야 함"""
        result = generate_research_brief('지속가능한 에너지')
        self.assertGreaterEqual(len(result.key_questions), 5)

    def test_key_questions_contain_topic(self):
        """핵심 질문에 주제가 포함되어야 함"""
        topic = '원격 근무'
        result = generate_research_brief(topic)
        for q in result.key_questions:
            self.assertIn(topic, q)

    def test_evidence_gaps_not_empty(self):
        """증거 갭이 비어있지 않아야 함"""
        result = generate_research_brief('디지털 전환')
        self.assertGreater(len(result.evidence_gaps), 0)

    def test_recommended_sources_not_empty(self):
        """참고 소스가 비어있지 않아야 함"""
        result = generate_research_brief('사이버 보안')
        self.assertGreater(len(result.recommended_sources), 0)

    def test_target_audience_not_empty(self):
        """대상 독자가 비어있지 않아야 함"""
        result = generate_research_brief('웹 개발 트렌드')
        self.assertGreater(len(result.target_audience), 0)

    def test_target_audience_specific_for_dev(self):
        """개발 관련 주제는 개발자 타겟이어야 함"""
        result = generate_research_brief('프론트엔드 개발')
        self.assertIn('개발자', result.target_audience)

    def test_target_audience_specific_for_investment(self):
        """투자 관련 주제는 투자자 타겟이어야 함"""
        result = generate_research_brief('해외 주식 투자')
        self.assertIn('투자', result.target_audience)

    def test_context_affects_audience(self):
        """context가 대상 독자 판별에 영향을 줘야 함"""
        # context에 '개발' 포함 → 개발자 타겟
        result = generate_research_brief('최적화 기법', context='소프트웨어 개발')
        self.assertIn('개발자', result.target_audience)

    def test_generic_topic_general_audience(self):
        """일반 주제는 범용 독자 타겟이어야 함"""
        result = generate_research_brief('미래 전망')
        self.assertIn('일반', result.target_audience)

    def test_deterministic_output(self):
        """동일 주제에 대해 동일한 결과를 반환해야 함"""
        result1 = generate_research_brief('블록체인 기술')
        result2 = generate_research_brief('블록체인 기술')
        self.assertEqual(result1.angles, result2.angles)
        self.assertEqual(result1.key_questions, result2.key_questions)
        self.assertEqual(result1.target_audience, result2.target_audience)


class TestDetermineTargetAudience(unittest.TestCase):
    """대상 독자 판별 테스트"""

    def test_cooking_keyword(self):
        """요리 키워드는 요리 관심 독자"""
        audience = _determine_target_audience('요리 초보')
        self.assertIn('요리', audience)

    def test_ai_keyword(self):
        """AI 키워드는 기술 전문가 독자"""
        audience = _determine_target_audience('ai 모델 학습')
        self.assertIn('AI', audience)

    def test_unknown_keyword(self):
        """매칭되지 않는 키워드는 일반 독자"""
        audience = _determine_target_audience('무작위 주제 xyz')
        self.assertIn('일반', audience)


if __name__ == '__main__':
    unittest.main()
