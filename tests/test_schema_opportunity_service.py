"""
Schema Opportunity Finder 서비스 테스트
"""
import unittest
import json

from services.seo.schema_opportunity_service import find_schema_opportunities


class TestSchemaOpportunityService(unittest.TestCase):
    """find_schema_opportunities() 함수 테스트."""

    # ── 1. 빈 입력 ──

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 빈 결과와 안내 메시지를 반환한다."""
        result = find_schema_opportunities('')
        self.assertEqual(result['opportunities'], [])
        self.assertEqual(result['total_opportunities'], 0)
        self.assertEqual(result['coverage_score'], 0.0)
        self.assertTrue(len(result['suggestions']) > 0)

        # None 입력도 동일
        result_none = find_schema_opportunities(None)
        self.assertEqual(result_none['total_opportunities'], 0)

        # 공백 문자열
        result_ws = find_schema_opportunities('   ')
        self.assertEqual(result_ws['total_opportunities'], 0)

    # ── 2. FAQPage 감지 ──

    def test_faq_detection(self):
        """질문형 소제목이 포함된 콘텐츠에서 FAQPage를 감지한다."""
        content = """
## Python이란 무엇인가요?
Python은 배우기 쉬운 프로그래밍 언어입니다.

## Python을 왜 배워야 할까요?
데이터 분석, 웹 개발, AI 등 다양한 분야에서 활용됩니다.

Q: Python 설치는 어렵나요?
아닙니다. 공식 사이트에서 간단히 설치할 수 있습니다.
"""
        result = find_schema_opportunities(content)
        types = [o['schema_type'] for o in result['opportunities']]
        self.assertIn('FAQPage', types)

        faq = next(o for o in result['opportunities'] if o['schema_type'] == 'FAQPage')
        self.assertGreater(faq['confidence'], 0)
        self.assertTrue(len(faq['evidence']) > 0)

    # ── 3. HowTo 감지 ──

    def test_howto_detection(self):
        """순서형 문장이 포함된 콘텐츠에서 HowTo를 감지한다."""
        content = """
## 김치 만드는 방법

준비물: 배추, 고춧가루, 마늘, 젓갈

1단계: 배추를 소금에 절입니다.
2단계: 양념장을 만듭니다.
3단계: 절인 배추에 양념을 버무립니다.
마지막으로 밀폐 용기에 담아 숙성시킵니다.
"""
        result = find_schema_opportunities(content)
        types = [o['schema_type'] for o in result['opportunities']]
        self.assertIn('HowTo', types)

        howto = next(o for o in result['opportunities'] if o['schema_type'] == 'HowTo')
        self.assertGreater(howto['confidence'], 0)

    # ── 4. VideoObject 감지 ──

    def test_video_object_detection(self):
        """타임스탬프와 영상 키워드가 포함된 콘텐츠에서 VideoObject를 감지한다."""
        content = """
이 영상에서는 Python 기초를 설명합니다.

[00:00] 소개
[02:30] 변수와 자료형
[05:15] 조건문과 반복문
[10:00] 함수 정의

YouTube에서 더 많은 강의를 확인하세요.
"""
        result = find_schema_opportunities(content)
        types = [o['schema_type'] for o in result['opportunities']]
        self.assertIn('VideoObject', types)

        video = next(o for o in result['opportunities'] if o['schema_type'] == 'VideoObject')
        self.assertGreater(video['confidence'], 30)

    # ── 5. DefinedTerm 감지 ──

    def test_defined_term_detection(self):
        """정의문이 포함된 콘텐츠에서 DefinedTerm을 감지한다."""
        content = """
머신러닝이란 데이터로부터 패턴을 학습하는 기술입니다.

딥러닝은 인공 신경망을 활용한 학습 방법을 말한다.

정의: 자연어 처리(NLP)는 컴퓨터가 인간의 언어를 이해하는 기술이다.

개념: 강화학습은 보상 신호를 통해 최적의 행동을 학습하는 방법이다.
"""
        result = find_schema_opportunities(content)
        types = [o['schema_type'] for o in result['opportunities']]
        self.assertIn('DefinedTerm', types)

        dt = next(o for o in result['opportunities'] if o['schema_type'] == 'DefinedTerm')
        self.assertGreater(dt['confidence'], 0)
        self.assertTrue(len(dt['evidence']) >= 2)

    # ── 6. ItemList 감지 ──

    def test_item_list_detection(self):
        """목록형 콘텐츠에서 ItemList를 감지한다."""
        content = """
# Top 5 프로그래밍 언어

1. Python - 데이터 과학과 AI에 강력
2. JavaScript - 웹 개발의 핵심
3. TypeScript - 타입 안전한 JavaScript
4. Go - 고성능 서버 개발
5. Rust - 메모리 안전한 시스템 프로그래밍

이 5가지 언어를 배우면 다양한 분야에 활용할 수 있습니다.
"""
        result = find_schema_opportunities(content)
        types = [o['schema_type'] for o in result['opportunities']]
        self.assertIn('ItemList', types)

        il = next(o for o in result['opportunities'] if o['schema_type'] == 'ItemList')
        self.assertGreater(il['confidence'], 30)

    # ── 7. 신뢰도 범위 ──

    def test_confidence_range(self):
        """모든 기회의 신뢰도가 0~100 범위 내에 있다."""
        content = """
## API란 무엇인가요?
API는 프로그램 간 통신 인터페이스를 말한다.

Step 1: API 키를 발급받습니다.
Step 2: 요청 URL을 구성합니다.

Top 3 인기 API:
1. Google Maps API
2. OpenAI API
3. Twitter API

[00:00] 소개
[03:00] 실습
"""
        result = find_schema_opportunities(content)
        for opp in result['opportunities']:
            self.assertGreaterEqual(opp['confidence'], 0)
            self.assertLessEqual(opp['confidence'], 100)

    # ── 8. JSON-LD 템플릿 ──

    def test_json_ld_template(self):
        """감지된 기회에 유효한 JSON-LD 템플릿이 포함되어 있다."""
        content = """
## React란 무엇인가요?
React는 사용자 인터페이스를 구축하기 위한 JavaScript 라이브러리입니다.
React의 핵심 개념은 컴포넌트 기반 아키텍처입니다.
"""
        result = find_schema_opportunities(content)
        self.assertGreater(len(result['opportunities']), 0)

        for opp in result['opportunities']:
            self.assertIn('json_ld_template', opp)
            # 유효한 JSON인지 확인
            parsed = json.loads(opp['json_ld_template'])
            self.assertIn('@context', parsed)
            self.assertEqual(parsed['@context'], 'https://schema.org')
            self.assertIn('@type', parsed)

    # ── 9. 우선순위 값 ──

    def test_priority_levels(self):
        """우선순위가 high/medium/low 중 하나이다."""
        content = """
## 도커란 무엇인가요?
도커는 컨테이너 기반 가상화 기술을 말한다.

Step 1: Dockerfile을 작성합니다.
Step 2: 이미지를 빌드합니다.
Step 3: 컨테이너를 실행합니다.

Top 5 도커 명령어:
1. docker build
2. docker run
3. docker ps
4. docker stop
5. docker rm
"""
        result = find_schema_opportunities(content)
        valid_priorities = {'high', 'medium', 'low'}
        for opp in result['opportunities']:
            self.assertIn(opp['priority'], valid_priorities)

    # ── 10. 여러 스키마 동시 감지 ──

    def test_multiple_schemas(self):
        """하나의 콘텐츠에서 여러 스키마 타입이 동시에 감지된다."""
        content = """
# 웹 개발 완전 가이드

## 웹 개발이란 무엇인가요?
웹 개발은 웹사이트를 만드는 과정을 말한다.

## 어떻게 시작할까요?
1단계: HTML을 배웁니다.
2단계: CSS를 배웁니다.
3단계: JavaScript를 배웁니다.

Top 3 프레임워크:
1. React
2. Vue
3. Angular

[00:00] 소개
[05:30] HTML 기초
[12:00] CSS 스타일링

이 영상에서 자세히 알아봅니다.
"""
        result = find_schema_opportunities(content)
        types = [o['schema_type'] for o in result['opportunities']]
        # 최소 3가지 이상 감지
        self.assertGreaterEqual(len(types), 3)
        # 중복 타입 없음
        self.assertEqual(len(types), len(set(types)))

    # ── 11. 커버리지 점수 ──

    def test_coverage_score(self):
        """커버리지 점수가 0~100 범위이다."""
        # 빈 콘텐츠: 0
        result_empty = find_schema_opportunities('')
        self.assertEqual(result_empty['coverage_score'], 0.0)

        # 콘텐츠가 있을 때: 0~100 범위
        content = """
## 쿠버네티스란 무엇인가요?
쿠버네티스는 컨테이너 오케스트레이션 플랫폼이다.

Step 1: 클러스터를 생성합니다.
"""
        result = find_schema_opportunities(content)
        self.assertGreaterEqual(result['coverage_score'], 0.0)
        self.assertLessEqual(result['coverage_score'], 100.0)

    # ── 12. 제안 생성 ──

    def test_suggestions(self):
        """감지 결과에 따른 제안이 생성된다."""
        # 빈 콘텐츠 제안
        result_empty = find_schema_opportunities('')
        self.assertTrue(len(result_empty['suggestions']) > 0)

        # 일부 스키마만 감지된 경우: 미감지 스키마에 대한 제안 포함
        content = """
## Git이란 무엇인가요?
Git은 분산 버전 관리 시스템을 말한다.
Git을 사용하면 코드 변경 이력을 추적할 수 있습니다.
"""
        result = find_schema_opportunities(content)
        self.assertTrue(len(result['suggestions']) > 0)
        # 제안이 문자열 리스트인지 확인
        for s in result['suggestions']:
            self.assertIsInstance(s, str)
            self.assertGreater(len(s), 0)

    # ── 13. Article 기본 감지 ──

    def test_article_detection(self):
        """충분한 길이의 콘텐츠에서 Article 스키마를 감지한다."""
        content = """
# 프로그래밍의 미래

프로그래밍은 현대 사회에서 가장 중요한 기술 중 하나입니다.
인공지능과 자동화가 발전하면서 프로그래밍의 역할도 변화하고 있습니다.

전통적인 프로그래밍 방식에서 벗어나 AI 기반 코딩 도구가 등장하고 있으며,
이러한 변화는 개발자의 역할을 재정의하고 있습니다.

앞으로 프로그래밍은 더 접근성이 높아지고, 더 많은 사람들이 코드를 작성하게 될 것입니다.
"""
        result = find_schema_opportunities(content)
        types = [o['schema_type'] for o in result['opportunities']]
        self.assertIn('Article', types)

    # ── 14. 반환 구조 검증 ──

    def test_return_structure(self):
        """반환 dict의 키와 타입이 올바르다."""
        content = "간단한 테스트 콘텐츠입니다. 충분히 긴 텍스트로 구조를 검증합니다. " * 10
        result = find_schema_opportunities(content)

        # 최상위 키 존재
        self.assertIn('opportunities', result)
        self.assertIn('total_opportunities', result)
        self.assertIn('coverage_score', result)
        self.assertIn('suggestions', result)

        # 타입 확인
        self.assertIsInstance(result['opportunities'], list)
        self.assertIsInstance(result['total_opportunities'], int)
        self.assertIsInstance(result['coverage_score'], float)
        self.assertIsInstance(result['suggestions'], list)

        # total_opportunities == len(opportunities)
        self.assertEqual(result['total_opportunities'], len(result['opportunities']))


if __name__ == '__main__':
    unittest.main()
