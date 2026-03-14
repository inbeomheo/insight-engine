"""section_drift_service 단위 테스트"""
import unittest

from services.quality.section_drift_service import (
    detect_section_drift,
    _extract_keywords,
)


class TestDetectSectionDrift(unittest.TestCase):

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 기본 응답 반환"""
        result = detect_section_drift('')
        self.assertEqual(result['sections'], [])
        self.assertEqual(result['overall_coherence'], 100.0)
        self.assertEqual(result['drifted_sections'], [])
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'][0])

    def test_no_headings(self):
        """헤딩이 없는 콘텐츠 → 섹션 없음, 제안 포함"""
        content = '이것은 헤딩 없이 작성된 콘텐츠입니다. 마크다운 헤딩이 없습니다.'
        result = detect_section_drift(content)
        self.assertEqual(result['sections'], [])
        self.assertTrue(any('헤딩' in s for s in result['suggestions']))

    def test_on_topic_section(self):
        """소제목과 본문이 일치하면 on_topic 판정"""
        content = """## 파이썬 프로그래밍

파이썬은 프로그래밍 언어입니다. 파이썬은 간결한 문법을 제공합니다.
파이썬으로 프로그래밍을 하면 생산성이 높아집니다.
파이썬 프로그래밍은 데이터 과학에서 많이 활용됩니다.
파이썬 프로그래밍의 장점은 라이브러리가 풍부하다는 것입니다."""
        result = detect_section_drift(content)
        self.assertEqual(len(result['sections']), 1)
        self.assertEqual(result['sections'][0]['status'], 'on_topic')

    def test_drifted_section(self):
        """소제목과 본문이 완전히 다르면 drifted 판정"""
        content = """## 파이썬 프로그래밍

오늘 점심 메뉴는 김치찌개였습니다. 저녁에는 치킨을 먹을 계획입니다.
맛있는 음식을 먹으면 기분이 좋아집니다. 요리를 잘하는 사람이 부럽습니다.
주말에는 카페에서 커피를 마시며 독서를 하겠습니다."""
        result = detect_section_drift(content)
        self.assertEqual(len(result['sections']), 1)
        self.assertEqual(result['sections'][0]['status'], 'drifted')

    def test_partial_drift(self):
        """헤딩 키워드가 본문에 약간만 등장하면 partial_drift"""
        content = """## 머신러닝 알고리즘

머신러닝은 데이터에서 패턴을 학습합니다.
그런데 요즘 날씨가 너무 좋습니다. 봄이 왔습니다. 산책을 자주 합니다.
공원에서 운동을 하면 건강에 좋습니다. 자전거 타기도 재미있습니다.
비타민을 섭취하면 면역력이 높아집니다. 건강 관리가 중요합니다.
머신러닝 관련 공부도 해야겠습니다."""
        result = detect_section_drift(content)
        section = result['sections'][0]
        # 헤딩 키워드가 아주 적게 등장 → partial_drift 또는 drifted
        self.assertIn(section['status'], ('partial_drift', 'drifted'))

    def test_relevance_score_range(self):
        """relevance_score는 0~1 범위"""
        content = """## 테스트 주제

테스트 본문입니다. 테스트를 진행합니다. 테스트가 중요합니다."""
        result = detect_section_drift(content)
        for section in result['sections']:
            self.assertGreaterEqual(section['relevance_score'], 0.0)
            self.assertLessEqual(section['relevance_score'], 1.0)

    def test_coherence_score_range(self):
        """overall_coherence는 0~100 범위"""
        content = """## 섹션 하나

본문 내용입니다. 섹션의 주제를 잘 유지합니다. 섹션에 대한 설명입니다."""
        result = detect_section_drift(content)
        self.assertGreaterEqual(result['overall_coherence'], 0.0)
        self.assertLessEqual(result['overall_coherence'], 100.0)

    def test_heading_keywords_extraction(self):
        """헤딩에서 키워드가 올바르게 추출되는지"""
        content = """## 인공지능 딥러닝 기초

인공지능과 딥러닝에 대한 기초 내용입니다."""
        result = detect_section_drift(content)
        heading_kws = result['sections'][0]['heading_keywords']
        self.assertIn('인공지능', heading_kws)
        self.assertIn('딥러닝', heading_kws)

    def test_drift_keywords(self):
        """drift_keywords는 헤딩에 없는 본문 상위 키워드"""
        content = """## 블록체인 기술

요리를 잘하려면 신선한 재료가 중요합니다. 요리 레시피를 따라하면 됩니다.
맛있는 요리를 만들면 가족이 행복해집니다. 요리 실력을 늘리세요.
베이킹도 재미있는 취미입니다. 빵을 직접 만들어 보세요."""
        result = detect_section_drift(content)
        drift_kws = result['sections'][0]['drift_keywords']
        # '요리' 등 헤딩과 무관한 키워드가 drift에 포함
        self.assertTrue(len(drift_kws) > 0)
        # 헤딩 키워드는 drift에 포함되지 않아야 함
        heading_kws = set(result['sections'][0]['heading_keywords'])
        for dk in drift_kws:
            self.assertNotIn(dk, heading_kws)

    def test_multiple_sections(self):
        """여러 섹션이 있을 때 각각 개별 분석"""
        content = """## 자바스크립트 기초

자바스크립트는 웹 개발 언어입니다. 자바스크립트로 프론트엔드를 만듭니다.
자바스크립트 기초를 배우면 웹 개발이 가능합니다.

## 리액트 프레임워크

리액트는 UI 라이브러리입니다. 리액트로 컴포넌트를 만듭니다.
리액트 프레임워크는 SPA 개발에 적합합니다.

## 데이터베이스 설계

데이터베이스는 정보를 저장합니다. 데이터베이스 설계는 정규화가 중요합니다.
데이터베이스에서 쿼리를 실행하여 데이터를 조회합니다."""
        result = detect_section_drift(content)
        self.assertEqual(len(result['sections']), 3)
        # 각 섹션에 필수 필드 존재
        for section in result['sections']:
            self.assertIn('heading', section)
            self.assertIn('relevance_score', section)
            self.assertIn('status', section)

    def test_drifted_sections_list(self):
        """drifted_sections에는 drifted 판정 섹션의 heading만 포함"""
        content = """## 클라우드 컴퓨팅

클라우드 컴퓨팅은 서버를 원격으로 이용하는 기술입니다.
클라우드 컴퓨팅으로 확장성을 확보할 수 있습니다.

## 네트워크 보안

오늘 저녁은 피자를 주문했습니다. 치즈가 듬뿍 들어간 피자가 맛있습니다.
주말에는 영화를 볼 계획입니다. 최근 개봉한 영화가 재미있다고 합니다."""
        result = detect_section_drift(content)
        # 첫 섹션은 on_topic, 두 번째는 drifted
        self.assertEqual(result['sections'][0]['status'], 'on_topic')
        self.assertEqual(result['sections'][1]['status'], 'drifted')
        self.assertIn('네트워크 보안', result['drifted_sections'])
        self.assertNotIn('클라우드 컴퓨팅', result['drifted_sections'])

    def test_suggestions(self):
        """이탈 섹션이 있으면 개선 제안이 생성됨"""
        content = """## 소프트웨어 테스팅

맛있는 음식 레시피를 소개합니다. 김치볶음밥은 간단하게 만들 수 있습니다.
계란 프라이를 올리면 더 맛있습니다. 참기름을 살짝 넣어주세요."""
        result = detect_section_drift(content)
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)
        # 이탈 관련 제안이 존재해야 함
        self.assertTrue(
            any('벗어났습니다' in s or '이탈' in s for s in result['suggestions'])
        )


class TestExtractKeywords(unittest.TestCase):

    def test_korean_keywords(self):
        """한국어 키워드 추출"""
        keywords = _extract_keywords('인공지능과 머신러닝을 활용한 데이터 분석')
        self.assertIn('인공지능', keywords)
        self.assertIn('머신러닝', keywords)

    def test_english_keywords(self):
        """영어 키워드 추출"""
        keywords = _extract_keywords('Python과 JavaScript를 배우세요')
        self.assertIn('python', keywords)
        self.assertIn('javascript', keywords)

    def test_stopwords_removed(self):
        """불용어가 제거되는지"""
        keywords = _extract_keywords('있습니다 합니다 됩니다 위해 통해')
        for sw in ['있습니다', '합니다', '됩니다', '위해', '통해']:
            self.assertNotIn(sw, keywords)


if __name__ == '__main__':
    unittest.main()
