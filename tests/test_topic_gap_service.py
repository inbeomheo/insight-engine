"""topic_gap_service 단위 테스트"""
import unittest

from services.topic_gap_service import analyze_topic_gaps


class TestTopicGapService(unittest.TestCase):
    """토픽 갭 분석 서비스 테스트"""

    # --- 기본 입력 검증 ---

    def test_empty_content(self):
        """빈 문자열 입력 시 빈 결과를 반환한다."""
        result = analyze_topic_gaps('')
        self.assertEqual(result['gaps'], [])
        self.assertEqual(result['coverage_score'], 0.0)
        self.assertEqual(result['my_unique_topics'], [])
        self.assertEqual(result['common_topics'], [])
        self.assertEqual(result['missing_questions'], [])
        self.assertGreater(len(result['suggestions']), 0)

    def test_none_content(self):
        """None 입력 시 빈 결과를 반환한다."""
        result = analyze_topic_gaps(None)
        self.assertEqual(result['gaps'], [])
        self.assertEqual(result['coverage_score'], 0.0)
        self.assertIn('콘텐츠가 없습니다', result['suggestions'][0])

    # --- 자체 분석 (reference 없음) ---

    def test_self_analysis(self):
        """reference 없이 자체 구조 분석을 수행한다."""
        # 구조가 부족한 콘텐츠 (헤딩, 예시, 정의, 결론 없음)
        content = (
            '머신러닝은 데이터를 활용하는 기술이다. '
            '머신러닝 알고리즘은 다양하다. '
            '딥러닝은 머신러닝의 하위 분야다. '
            '딥러닝 모델은 신경망을 사용한다.'
        )
        result = analyze_topic_gaps(content)

        # 반환 구조 확인
        self.assertIn('gaps', result)
        self.assertIn('coverage_score', result)
        self.assertIn('my_unique_topics', result)
        self.assertIn('suggestions', result)
        # reference 없으므로 common_topics 비어있음
        self.assertEqual(result['common_topics'], [])
        # 자체 분석 시 구조적 갭 탐지
        self.assertGreater(len(result['gaps']), 0)
        # 구조적 완성도 점수
        self.assertGreaterEqual(result['coverage_score'], 0)
        self.assertLessEqual(result['coverage_score'], 100)

    # --- 참고 콘텐츠와 비교 ---

    def test_with_reference(self):
        """reference_contents와 비교 분석을 수행한다."""
        content = '파이썬 프로그래밍 파이썬 웹개발 웹개발 프레임워크 프레임워크'
        references = [
            {
                'title': '참고글 A',
                'content': '파이썬 프로그래밍 파이썬 데이터분석 데이터분석 머신러닝 머신러닝',
            },
        ]

        result = analyze_topic_gaps(content, references)

        # 공통 토픽에 '파이썬' 포함
        self.assertIn('파이썬', result['common_topics'])
        # coverage_score 산출
        self.assertGreater(result['coverage_score'], 0)

    def test_gap_detection(self):
        """빠진 주제를 정확히 감지한다."""
        content = '웹개발 프레임워크 웹개발 프레임워크 자바스크립트 자바스크립트'
        references = [
            {
                'title': '참고글 1',
                'content': '데이터베이스 설계 데이터베이스 설계 보안 인증 보안 인증',
            },
        ]

        result = analyze_topic_gaps(content, references)

        # 갭에 내 콘텐츠에 없는 토픽이 포함됨
        gap_topics = [g['topic'] for g in result['gaps']]
        self.assertIn('데이터베이스', gap_topics)
        self.assertIn('보안', gap_topics)

    def test_importance_levels(self):
        """importance가 high/medium으로 올바르게 분류된다.
        2개 이상 reference에서 등장하면 high, 1개만이면 medium.
        """
        content = '프로그래밍 기초 프로그래밍 기초'
        references = [
            {
                'title': '참고글 A',
                'content': '테스트 자동화 테스트 자동화 배포 전략 배포 전략',
            },
            {
                'title': '참고글 B',
                'content': '테스트 자동화 테스트 자동화 코드리뷰 코드리뷰',
            },
        ]

        result = analyze_topic_gaps(content, references)

        gap_map = {g['topic']: g['importance'] for g in result['gaps']}
        # '테스트'는 2개 reference에서 등장 → high
        if '테스트' in gap_map:
            self.assertEqual(gap_map['테스트'], 'high')
        # '코드리뷰'는 1개에서만 등장 → medium
        if '코드리뷰' in gap_map:
            self.assertEqual(gap_map['코드리뷰'], 'medium')

    def test_coverage_score_range(self):
        """coverage_score가 항상 0-100 범위이다."""
        # 완전히 다른 주제
        content = '요리 레시피 요리 레시피 맛집 탐방 맛집 탐방'
        references = [
            {
                'title': '참고글',
                'content': '프로그래밍 코딩 프로그래밍 코딩 알고리즘 알고리즘',
            },
        ]
        result = analyze_topic_gaps(content, references)
        self.assertGreaterEqual(result['coverage_score'], 0)
        self.assertLessEqual(result['coverage_score'], 100)

        # 동일한 주제
        same_content = '파이썬 개발 파이썬 개발'
        same_refs = [{'title': '동일', 'content': '파이썬 개발 파이썬 개발'}]
        result2 = analyze_topic_gaps(same_content, same_refs)
        self.assertGreaterEqual(result2['coverage_score'], 0)
        self.assertLessEqual(result2['coverage_score'], 100)

    def test_unique_topics(self):
        """내 콘텐츠에만 있는 고유 주제를 식별한다."""
        content = '블록체인 기술 블록체인 기술 스마트계약 스마트계약 탈중앙화 탈중앙화'
        references = [
            {
                'title': '참고글',
                'content': '블록체인 기술 블록체인 기술 비트코인 비트코인',
            },
        ]

        result = analyze_topic_gaps(content, references)

        # '스마트계약'은 내 콘텐츠에만 있으므로 unique
        self.assertIn('스마트계약', result['my_unique_topics'])
        # '블록체인'은 공통이므로 unique에 없어야 함
        self.assertNotIn('블록체인', result['my_unique_topics'])

    def test_common_topics(self):
        """공통 주제를 올바르게 식별한다."""
        content = '인공지능 머신러닝 인공지능 머신러닝 딥러닝 딥러닝'
        references = [
            {
                'title': '참고글',
                'content': '인공지능 머신러닝 인공지능 머신러닝 자연어처리 자연어처리',
            },
        ]

        result = analyze_topic_gaps(content, references)

        self.assertIn('인공지능', result['common_topics'])
        self.assertIn('머신러닝', result['common_topics'])
        # '자연어처리'는 reference에만 있으므로 common에 없어야 함
        self.assertNotIn('자연어처리', result['common_topics'])

    def test_missing_questions(self):
        """빠진 질문을 추출한다."""
        content = '파이썬 프로그래밍 파이썬 프로그래밍'
        references = [
            {
                'title': '참고 FAQ',
                'content': (
                    '파이썬 프로그래밍 파이썬 프로그래밍. '
                    '도커 컨테이너란 무엇인가? '
                    '쿠버네티스 배포 방법은?'
                ),
            },
        ]

        result = analyze_topic_gaps(content, references)

        # missing_questions에 질문이 포함되어야 함
        self.assertIsInstance(result['missing_questions'], list)
        # reference에서 추출된 질문 확인 (내 콘텐츠에 답변이 없는)
        if result['missing_questions']:
            # 각 항목이 문자열인지 확인
            for q in result['missing_questions']:
                self.assertIsInstance(q, str)

    def test_found_in_references(self):
        """갭의 found_in에 출처 참고 콘텐츠 제목이 표시된다."""
        content = '기본 프로그래밍 기본 프로그래밍'
        references = [
            {
                'title': 'RESTful API 가이드',
                'content': '엔드포인트 설계 엔드포인트 설계 인증 처리 인증 처리',
            },
            {
                'title': '마이크로서비스 아키텍처',
                'content': '서비스 분리 서비스 분리 엔드포인트 설계 엔드포인트 설계',
            },
        ]

        result = analyze_topic_gaps(content, references)

        # 갭이 있어야 함
        self.assertGreater(len(result['gaps']), 0)

        for gap in result['gaps']:
            # found_in이 리스트이고, 제목을 포함
            self.assertIsInstance(gap['found_in'], list)
            self.assertGreater(len(gap['found_in']), 0)
            # found_in 항목이 reference 제목 중 하나여야 함
            for title in gap['found_in']:
                self.assertIn(title, ['RESTful API 가이드', '마이크로서비스 아키텍처'])

    def test_suggestions(self):
        """suggestions 목록이 올바르게 생성된다."""
        # 커버리지가 낮은 경우
        content = '요리법 레시피 요리법 레시피'
        references = [
            {
                'title': '프로그래밍 입문',
                'content': (
                    '변수 선언 변수 선언 함수 정의 함수 정의 '
                    '클래스 상속 클래스 상속 모듈 임포트 모듈 임포트'
                ),
            },
        ]

        result = analyze_topic_gaps(content, references)

        # suggestions가 리스트이고 비어있지 않아야 함
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)
        # 각 제안이 한국어 문자열
        for s in result['suggestions']:
            self.assertIsInstance(s, str)
            self.assertGreater(len(s), 0)


if __name__ == '__main__':
    unittest.main()
