"""
AEO Optimizer Service 단위 테스트

AI Answer Engine Optimizer의 규칙 기반 채점 로직을 검증한다.
"""
import unittest

from services.aeo_optimizer_service import analyze_aeo


class TestAeoOptimizerService(unittest.TestCase):
    """AEO 분석 함수 테스트"""

    # === 1. 빈 콘텐츠 ===
    def test_empty_content(self):
        """빈 문자열 입력 시 점수 0, 등급 F를 반환해야 한다."""
        result = analyze_aeo('')
        self.assertEqual(result['aeo_score'], 0.0)
        self.assertEqual(result['grade'], 'F')
        self.assertIsNone(result['query_alignment'])
        self.assertIsInstance(result['optimizations'], list)
        self.assertIsInstance(result['suggestions'], list)

    # === 2. None 입력 ===
    def test_none_content(self):
        """None 입력 시 에러 없이 점수 0을 반환해야 한다."""
        result = analyze_aeo(None)
        self.assertEqual(result['aeo_score'], 0.0)
        self.assertEqual(result['grade'], 'F')
        # factors 전부 0이어야 함
        for factor_name, factor_score in result['factors'].items():
            self.assertEqual(factor_score, 0.0, f"{factor_name}이 0이어야 함")

    # === 3. 기본 분석 ===
    def test_basic_analysis(self):
        """기본 콘텐츠를 분석하면 필수 키가 모두 반환되어야 한다."""
        content = "Python은 프로그래밍 언어이다. 간결한 문법이 특징이다."
        result = analyze_aeo(content)

        # 필수 키 확인
        required_keys = ['aeo_score', 'grade', 'factors', 'optimizations',
                         'query_alignment', 'summary', 'suggestions']
        for key in required_keys:
            self.assertIn(key, result, f"'{key}' 키가 결과에 포함되어야 함")

        # factors 하위 키 확인
        factor_keys = ['direct_answer', 'structured_data', 'authority_signals',
                       'clarity', 'citation_worthiness']
        for key in factor_keys:
            self.assertIn(key, result['factors'], f"factors에 '{key}'가 포함되어야 함")

    # === 4. 점수 범위 ===
    def test_score_range(self):
        """모든 점수가 0-100 범위 내에 있어야 한다."""
        content = """
## 머신러닝(Machine Learning) 개요

머신러닝이란 데이터를 기반으로 학습하는 AI 기술을 말한다.
2025년 기준으로 전 세계 AI 시장의 약 60%를 차지한다.
따라서 현대 소프트웨어 개발에서 필수 역량이다.

## 주요 유형

- 지도학습(Supervised Learning): 라벨이 있는 데이터로 학습
- 비지도학습(Unsupervised Learning): 라벨 없이 패턴 발견
- 강화학습(Reinforcement Learning): 보상 기반 학습

## 정리

머신러닝은 다양한 산업에 활용되고 있다.
"""
        result = analyze_aeo(content, '머신러닝이란 무엇인가')

        self.assertGreaterEqual(result['aeo_score'], 0)
        self.assertLessEqual(result['aeo_score'], 100)

        for factor_name, factor_score in result['factors'].items():
            self.assertGreaterEqual(factor_score, 0, f"{factor_name} >= 0")
            self.assertLessEqual(factor_score, 100, f"{factor_name} <= 100")

        if result['query_alignment'] is not None:
            self.assertGreaterEqual(result['query_alignment'], 0)
            self.assertLessEqual(result['query_alignment'], 100)

    # === 5. 등급 매핑 ===
    def test_grade_mapping(self):
        """점수에 따라 올바른 등급이 매핑되어야 한다."""
        # F등급 (빈 콘텐츠)
        result_f = analyze_aeo('')
        self.assertEqual(result_f['grade'], 'F')

        # 최소한의 콘텐츠 → 등급은 A~F 중 하나
        result = analyze_aeo("간단한 테스트 문장이다.")
        self.assertIn(result['grade'], ['A', 'B', 'C', 'D', 'F'])

    # === 6. 고품질 AEO 콘텐츠 ===
    def test_high_aeo_content(self):
        """정의, 구조, 통계, 출처 등을 모두 갖춘 콘텐츠는 높은 점수를 받아야 한다."""
        content = """## 클라우드 컴퓨팅(Cloud Computing)이란?

클라우드 컴퓨팅이란 인터넷을 통해 컴퓨팅 자원을 제공하는 기술을 말한다.

2025년 가트너 보고서에 따르면 글로벌 클라우드 시장은 약 6,000억 달러 규모이며, 연평균 20% 성장하고 있다.
따라서 기업의 디지털 전환에서 핵심 기술로 자리잡았다.

## 주요 서비스 모델

| 모델 | 설명 | 예시 |
|------|------|------|
| IaaS(Infrastructure as a Service) | 인프라 제공 | AWS EC2 |
| PaaS(Platform as a Service) | 플랫폼 제공 | Google App Engine |
| SaaS(Software as a Service) | 소프트웨어 제공 | Salesforce |

## 도입 방법

분석 결과 클라우드 도입 성공률을 높이려면 다음 단계를 따르세요:

1. 현재 인프라 분석
2. 마이그레이션(Migration) 전략 수립
3. 파일럿 프로젝트 실행

## FAQ

Q: 클라우드는 안전한가요?
A: 주요 클라우드 업체는 ISO 27001 인증을 보유하고 있습니다.

## 결론

클라우드 컴퓨팅은 비용 절감과 확장성 면에서 탁월하다.
올해 도입을 고려하고 있다면 소규모 프로젝트부터 시작해 보세요.
"""
        result = analyze_aeo(content)
        # 고품질 콘텐츠 → 65점(B등급) 이상 기대
        self.assertGreaterEqual(result['aeo_score'], 65,
                                f"고품질 콘텐츠인데 점수가 낮음: {result['aeo_score']}")
        self.assertIn(result['grade'], ['A', 'B'])

    # === 7. 저품질 AEO 콘텐츠 ===
    def test_low_aeo_content(self):
        """구조도 없고 정보도 부족한 콘텐츠는 낮은 점수를 받아야 한다."""
        content = (
            "그냥 아무 생각 없이 쓴 글이다 오늘 날씨가 좋아서 기분이 좋다 "
            "별로 할 말은 없지만 그래도 뭔가 써야 할 것 같아서 쓰고 있다 "
            "내일은 뭘 할지 모르겠다 그냥 그렇다"
        )
        result = analyze_aeo(content)
        # 저품질 → 50점(C등급) 미만 기대
        self.assertLess(result['aeo_score'], 50,
                        f"저품질 콘텐츠인데 점수가 높음: {result['aeo_score']}")
        self.assertIn(result['grade'], ['D', 'F'])

    # === 8. 직접 답변 점수 ===
    def test_direct_answer_scoring(self):
        """정의형 문장과 요약 섹션이 있으면 direct_answer 점수가 높아야 한다."""
        content_with_definition = """API란 소프트웨어 간 통신을 위한 인터페이스를 말한다.

## 요약

API는 현대 소프트웨어의 핵심이다.
"""
        result = analyze_aeo(content_with_definition)
        # 정의(+30) + 요약(+20) = 최소 50 이상
        self.assertGreaterEqual(result['factors']['direct_answer'], 50)

    # === 9. 구조화 점수 ===
    def test_structured_data_scoring(self):
        """마크다운 헤딩, 목록, 표가 있으면 structured_data 점수가 높아야 한다."""
        content = """## 섹션 1

내용 1

## 섹션 2

- 항목 A
- 항목 B
- 항목 C

## 섹션 3

| 열1 | 열2 |
|-----|-----|
| 값1 | 값2 |
"""
        result = analyze_aeo(content)
        # 헤딩 3개(+25) + 목록 3개(+25) + 표(+25) = 75
        self.assertGreaterEqual(result['factors']['structured_data'], 75)

    # === 10. 권위 신호 점수 ===
    def test_authority_signals(self):
        """통계, 출처, 날짜가 포함되면 authority_signals 점수가 높아야 한다."""
        content = """2025년 맥킨지 보고서에 따르면 AI 도입률은 56%에 달한다.
연구 결과 생산성이 약 2.5배 향상되었다.
API(Application Programming Interface)는 핵심 기술이다.
마이크로서비스(Microservice)는 확장성을 제공한다.
컨테이너(Container)는 배포를 단순화한다.
"""
        result = analyze_aeo(content)
        # 통계(+25) + 출처(+25) + 날짜(+25) + 전문 용어 3개(+25) = 100
        self.assertGreaterEqual(result['factors']['authority_signals'], 75)

    # === 11. 명확성 점수 ===
    def test_clarity_scoring(self):
        """짧은 문장, 괄호 설명, 접속사가 있으면 clarity 점수가 높아야 한다."""
        content = """API(Application Programming Interface)를 알아보자.
REST(Representational State Transfer)가 대표적이다.
따라서 웹 개발에 필수적이다.
또한 모바일 앱에서도 널리 사용된다.
그러므로 개발자라면 반드시 알아야 한다.

HTTP(Hypertext Transfer Protocol)를 기반으로 동작한다.
즉 인터넷 표준을 따른다.
특히 JSON 형식을 주로 사용한다.
"""
        result = analyze_aeo(content)
        # 짧은 문장(+25) + 괄호 설명(+25) + 접속사(+25) = 75+
        self.assertGreaterEqual(result['factors']['clarity'], 50)

    # === 12. 쿼리 정합성 (target_query 제공 시) ===
    def test_query_alignment(self):
        """target_query를 제공하면 query_alignment가 숫자로 반환되어야 한다."""
        content = """## 파이썬 설치 방법

파이썬을 설치하려면 다음 단계를 따르세요.
파이썬은 공식 사이트에서 다운로드할 수 있습니다.
파이썬 설치 후 환경변수를 설정하면 됩니다.

1. python.org 접속
2. 최신 버전 다운로드
3. 설치 마법사 실행
"""
        result = analyze_aeo(content, '파이썬 어떻게 설치')
        self.assertIsNotNone(result['query_alignment'])
        self.assertIsInstance(result['query_alignment'], float)
        # "파이썬"이 본문에 3회+, "어떻게" 의도 매칭 → 높은 점수 기대
        self.assertGreaterEqual(result['query_alignment'], 60)

    # === 13. target_query 미제공 시 None ===
    def test_query_alignment_none(self):
        """target_query를 제공하지 않으면 query_alignment가 None이어야 한다."""
        result = analyze_aeo("테스트 콘텐츠입니다.")
        self.assertIsNone(result['query_alignment'])

        # 빈 문자열도 None
        result2 = analyze_aeo("테스트 콘텐츠입니다.", '')
        self.assertIsNone(result2['query_alignment'])

    # === 14. 최적화 제안 ===
    def test_optimizations(self):
        """점수가 낮은 항목에 대해 최적화 제안이 생성되어야 한다."""
        # 구조화가 없는 단순 텍스트 → structured_data가 낮을 것
        content = "단순한 텍스트다. 구조가 없다. 그냥 글이다."
        result = analyze_aeo(content)

        self.assertIsInstance(result['optimizations'], list)
        # 최소 1개 이상의 최적화 제안이 있어야 함
        self.assertGreater(len(result['optimizations']), 0)

        # 최적화 제안의 구조 검증
        for opt in result['optimizations']:
            self.assertIn('category', opt)
            self.assertIn('issue', opt)
            self.assertIn('fix', opt)
            self.assertIn('impact', opt)
            self.assertIn(opt['impact'], ['high', 'medium', 'low'])


if __name__ == '__main__':
    unittest.main()
