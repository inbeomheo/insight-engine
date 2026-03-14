"""
수치 약속 이행 검증 서비스 테스트
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.analysis.numerical_promise_service import check_numerical_promises


class TestNumericalPromiseService(unittest.TestCase):
    """check_numerical_promises 함수 테스트"""

    # --- 기본 케이스 ---

    def test_empty_content(self):
        """빈 콘텐츠 처리"""
        result = check_numerical_promises('')
        self.assertEqual(result['promises'], [])
        self.assertEqual(result['integrity_score'], 100.0)
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'])

        # None 입력도 안전하게 처리
        result2 = check_numerical_promises(None)
        self.assertEqual(result2['promises'], [])

    def test_no_promises(self):
        """수치 약속이 없는 콘텐츠"""
        content = """# 프로그래밍 입문 가이드

파이썬은 배우기 쉬운 언어입니다.
변수, 조건문, 반복문을 익히면 됩니다.
"""
        result = check_numerical_promises(content)
        self.assertEqual(result['promises'], [])
        self.assertEqual(result['integrity_score'], 100.0)
        self.assertIn('수치 약속이 감지되지 않았습니다.', result['suggestions'])

    # --- 패턴 감지 ---

    def test_n_gaji_detection(self):
        """'N가지' 패턴 감지"""
        content = """# 생산성을 높이는 5가지 방법

1. 아침 루틴을 만들자
2. 집중 시간을 확보하자
3. 메모 습관을 들이자
4. 운동을 꾸준히 하자
5. 충분히 수면하자
"""
        result = check_numerical_promises(content)
        self.assertEqual(len(result['promises']), 1)
        self.assertEqual(result['promises'][0]['promised_number'], 5)
        self.assertEqual(result['promises'][0]['text'], '5가지')

    def test_n_steps_detection(self):
        """'N단계' 패턴 감지"""
        content = """# 3단계 설치 가이드

## 1단계: 다운로드
파일을 다운로드합니다.

## 2단계: 설치
설치 프로그램을 실행합니다.

## 3단계: 설정
초기 설정을 합니다.
"""
        result = check_numerical_promises(content)
        promises = [p for p in result['promises'] if p['text'] == '3단계']
        self.assertTrue(len(promises) >= 1)
        self.assertEqual(promises[0]['promised_number'], 3)

    def test_top_n_detection(self):
        """'Top N' 패턴 감지"""
        content = """# Top 3 추천 도서

1. 클린 코드
2. 리팩터링
3. 디자인 패턴
"""
        result = check_numerical_promises(content)
        top_promises = [p for p in result['promises'] if 'Top' in p['text'] or 'top' in p['text']]
        self.assertTrue(len(top_promises) >= 1)
        self.assertEqual(top_promises[0]['promised_number'], 3)

    # --- 이행 상태 판정 ---

    def test_match_status(self):
        """약속과 실제 항목이 정확히 일치 → match"""
        content = """# 코딩 3가지 원칙

1. 가독성
2. 유지보수성
3. 테스트 가능성
"""
        result = check_numerical_promises(content)
        self.assertEqual(len(result['promises']), 1)
        self.assertEqual(result['promises'][0]['status'], 'match')
        self.assertEqual(result['promises'][0]['actual_count'], 3)

    def test_mismatch_status(self):
        """약속과 실제 항목이 크게 다름 → mismatch"""
        content = """# 성공의 10가지 비결

1. 열정
2. 인내
"""
        result = check_numerical_promises(content)
        self.assertEqual(len(result['promises']), 1)
        self.assertEqual(result['promises'][0]['status'], 'mismatch')
        self.assertTrue(result['promises'][0]['actual_count'] < result['promises'][0]['promised_number'])

    def test_partial_match(self):
        """절반 이상 이행되었으나 완전하지 않음 → partial"""
        content = """# 건강을 위한 4가지 습관

1. 규칙적 수면
2. 균형 잡힌 식사
3. 꾸준한 운동
"""
        result = check_numerical_promises(content)
        self.assertEqual(len(result['promises']), 1)
        promise = result['promises'][0]
        self.assertEqual(promise['status'], 'partial')
        self.assertEqual(promise['promised_number'], 4)
        self.assertEqual(promise['actual_count'], 3)

    # --- 점수 및 복합 케이스 ---

    def test_integrity_score_range(self):
        """무결성 점수가 0~100 범위"""
        # 완전 일치
        content_match = """# 2가지 팁

1. 팁 하나
2. 팁 둘
"""
        result = check_numerical_promises(content_match)
        self.assertGreaterEqual(result['integrity_score'], 0.0)
        self.assertLessEqual(result['integrity_score'], 100.0)

        # 완전 불일치
        content_miss = """# 10가지 방법

내용이 없습니다.
"""
        result2 = check_numerical_promises(content_miss)
        self.assertGreaterEqual(result2['integrity_score'], 0.0)
        self.assertLessEqual(result2['integrity_score'], 100.0)
        self.assertLess(result2['integrity_score'], result['integrity_score'])

    def test_multiple_promises(self):
        """여러 수치 약속이 동시에 존재하는 경우"""
        content = """# 3가지 규칙으로 배우는 5단계 프로세스

## 3가지 규칙
1. 단순화
2. 자동화
3. 반복

## 5단계 프로세스
1. 분석
2. 설계
3. 구현
4. 테스트
5. 배포
"""
        result = check_numerical_promises(content)
        self.assertGreaterEqual(len(result['promises']), 2)

    # --- 번호 목록 카운팅 ---

    def test_numbered_list_counting(self):
        """다양한 번호 매기기 형식 인식"""
        # 괄호 형식
        content = """# 3가지 방법

1) 첫 번째 방법
2) 두 번째 방법
3) 세 번째 방법
"""
        result = check_numerical_promises(content)
        self.assertEqual(result['promises'][0]['actual_count'], 3)
        self.assertEqual(result['promises'][0]['status'], 'match')

    def test_korean_ordinal_counting(self):
        """한국어 서수(첫째, 둘째) 인식"""
        content = """# 3가지 핵심 가치

첫째, 정직함이 중요합니다.
둘째, 성실함을 갖춰야 합니다.
셋째, 창의성을 발휘해야 합니다.
"""
        result = check_numerical_promises(content)
        self.assertEqual(len(result['promises']), 1)
        self.assertEqual(result['promises'][0]['actual_count'], 3)
        self.assertEqual(result['promises'][0]['status'], 'match')

    # --- 제안 ---

    def test_suggestions(self):
        """개선 제안이 적절히 생성되는지 확인"""
        # 완전 일치 → 긍정적 제안
        content_ok = """# 2가지 팁

1. 집중하기
2. 쉬기
"""
        result_ok = check_numerical_promises(content_ok)
        self.assertTrue(any('이행' in s for s in result_ok['suggestions']))

        # 불일치 → 개선 제안
        content_bad = """# 5가지 비법

1. 유일한 비법
"""
        result_bad = check_numerical_promises(content_bad)
        self.assertTrue(any('부족' in s for s in result_bad['suggestions']))

    def test_subheading_counting(self):
        """소제목(##) 기반 카운팅"""
        content = """# 3가지 핵심 전략

## 전략 1: 시장 분석
시장을 먼저 분석합니다.

## 전략 2: 경쟁사 조사
경쟁사를 파악합니다.

## 전략 3: 차별화 포인트
차별화 전략을 수립합니다.
"""
        result = check_numerical_promises(content)
        self.assertEqual(len(result['promises']), 1)
        self.assertEqual(result['promises'][0]['status'], 'match')
        self.assertEqual(result['promises'][0]['actual_count'], 3)

    def test_n_gae_detection(self):
        """'N개' 패턴 감지"""
        content = """## 알아야 할 4개 포인트

1. 포인트 A
2. 포인트 B
3. 포인트 C
4. 포인트 D
"""
        result = check_numerical_promises(content)
        gae_promises = [p for p in result['promises'] if '개' in p['text']]
        self.assertTrue(len(gae_promises) >= 1)
        self.assertEqual(gae_promises[0]['promised_number'], 4)
        self.assertEqual(gae_promises[0]['status'], 'match')

    def test_overcounting_mismatch(self):
        """약속보다 초과 항목 → mismatch"""
        content = """# 2가지 방법

1. 방법 A
2. 방법 B
3. 방법 C
4. 방법 D
5. 방법 E
"""
        result = check_numerical_promises(content)
        self.assertEqual(result['promises'][0]['status'], 'mismatch')
        self.assertGreater(result['promises'][0]['actual_count'], result['promises'][0]['promised_number'])


if __name__ == '__main__':
    unittest.main()
