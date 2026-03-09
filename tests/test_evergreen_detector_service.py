"""
에버그린 감지 서비스 테스트

detect_expiry_signals, is_evergreen, get_evergreen_score 검증.
"""
import unittest
from services.evergreen_detector_service import (
    ExpirySignal,
    detect_expiry_signals,
    is_evergreen,
    get_evergreen_score,
)


class TestDetectExpirySignals(unittest.TestCase):
    """detect_expiry_signals 함수 테스트"""

    def test_empty_content_returns_empty(self):
        """빈 콘텐츠 → 빈 리스트"""
        self.assertEqual(detect_expiry_signals(''), [])
        self.assertEqual(detect_expiry_signals('   '), [])
        self.assertEqual(detect_expiry_signals(None), [])

    def test_detect_korean_date(self):
        """한국어 날짜 감지: 2024년 3월"""
        signals = detect_expiry_signals('2024년 3월에 출시된 제품입니다.')
        date_signals = [s for s in signals if s.signal_type == 'date']
        self.assertGreaterEqual(len(date_signals), 1)
        self.assertEqual(date_signals[0].severity, 'high')

    def test_detect_iso_date(self):
        """ISO 날짜 감지: 2024-03-15"""
        signals = detect_expiry_signals('업데이트 날짜: 2024-03-15')
        date_signals = [s for s in signals if s.signal_type == 'date']
        self.assertGreaterEqual(len(date_signals), 1)

    def test_detect_english_month_year(self):
        """영어 월 + 연도 감지: March 2024"""
        signals = detect_expiry_signals('Published in March 2024.')
        date_signals = [s for s in signals if s.signal_type == 'date']
        self.assertGreaterEqual(len(date_signals), 1)

    def test_detect_relative_time_ko(self):
        """상대적 시간 표현 감지: 올해, 작년, 최근 3개월"""
        content = '올해 가장 인기 있는 프레임워크. 최근 6개월 트렌드.'
        signals = detect_expiry_signals(content)
        date_signals = [s for s in signals if s.signal_type == 'date']
        self.assertGreaterEqual(len(date_signals), 2)

    def test_detect_statistic_percent(self):
        """통계(%) 감지"""
        signals = detect_expiry_signals('시장 점유율이 78%로 상승했습니다.')
        stat_signals = [s for s in signals if s.signal_type == 'statistic']
        self.assertGreaterEqual(len(stat_signals), 1)
        self.assertEqual(stat_signals[0].severity, 'high')

    def test_detect_statistic_count(self):
        """통계(명/건) 감지"""
        signals = detect_expiry_signals('사용자 100만명 돌파')
        stat_signals = [s for s in signals if s.signal_type == 'statistic']
        self.assertGreaterEqual(len(stat_signals), 1)

    def test_detect_product_name(self):
        """제품명 감지: iPhone 15"""
        signals = detect_expiry_signals('iPhone 15 Pro Max는 성능이 좋습니다.')
        prod_signals = [s for s in signals if s.signal_type == 'product_name']
        self.assertGreaterEqual(len(prod_signals), 1)
        self.assertEqual(prod_signals[0].severity, 'medium')

    def test_detect_version(self):
        """버전 감지: Python 3.12, v2.0.1"""
        content = 'Python 3.12에서 새로운 기능이 추가되었습니다. v2.0.1 패치.'
        signals = detect_expiry_signals(content)
        ver_signals = [s for s in signals if s.signal_type == 'version']
        self.assertGreaterEqual(len(ver_signals), 1)

    def test_detect_event(self):
        """이벤트 감지: WWDC 2024"""
        signals = detect_expiry_signals('WWDC 2024에서 발표된 내용.')
        event_signals = [s for s in signals if s.signal_type == 'event']
        self.assertGreaterEqual(len(event_signals), 1)
        self.assertEqual(event_signals[0].severity, 'low')

    def test_sorted_by_position(self):
        """결과가 position 오름차순 정렬"""
        content = '2024년 제품 출시. iPhone 15 리뷰. 점유율 50% 달성.'
        signals = detect_expiry_signals(content)
        positions = [s.position for s in signals]
        self.assertEqual(positions, sorted(positions))

    def test_no_duplicates(self):
        """동일 위치+텍스트 중복 없음"""
        content = '2024년 3월 보고서'
        signals = detect_expiry_signals(content)
        keys = [(s.position, s.text) for s in signals]
        self.assertEqual(len(keys), len(set(keys)))

    def test_evergreen_content_no_signals(self):
        """에버그린 콘텐츠 → 신호 없음 또는 매우 적음"""
        content = (
            '좋은 코드를 작성하는 방법에 대해 알아봅시다. '
            '변수 이름은 의미를 담아야 합니다. '
            '함수는 하나의 역할만 수행해야 합니다.'
        )
        signals = detect_expiry_signals(content)
        # 날짜/통계/제품명 등이 없으므로 매우 적어야 함
        self.assertLessEqual(len(signals), 1)


class TestIsEvergreen(unittest.TestCase):
    """is_evergreen 함수 테스트"""

    def test_evergreen_simple(self):
        """시간 독립적 콘텐츠 → True"""
        content = '좋은 습관은 매일 조금씩 실천하는 것입니다.'
        self.assertTrue(is_evergreen(content))

    def test_not_evergreen_many_dates(self):
        """날짜/통계가 많은 콘텐츠 → False"""
        content = (
            '2024년 1분기 매출은 50억원. 2023년 대비 25% 성장. '
            '2024년 3월 기준 사용자 100만명. 올해 목표는 200만명. '
            'iPhone 15 출시와 함께 시장 변화.'
        )
        self.assertFalse(is_evergreen(content, threshold=3))

    def test_threshold_parameter(self):
        """threshold 파라미터 동작 확인"""
        content = '2024년 출시. 2025년 업데이트. 점유율 30%.'
        # 신호가 3개 정도 예상 — threshold 높이면 evergreen 판정
        signals = detect_expiry_signals(content)
        high_threshold = len(signals) + 5
        self.assertTrue(is_evergreen(content, threshold=high_threshold))

    def test_empty_is_evergreen(self):
        """빈 콘텐츠 → True (신호 0개 ≤ threshold)"""
        self.assertTrue(is_evergreen(''))


class TestGetEvergreenScore(unittest.TestCase):
    """get_evergreen_score 함수 테스트"""

    def test_empty_content_perfect_score(self):
        """빈 콘텐츠 → 100점"""
        self.assertEqual(get_evergreen_score(''), 100.0)

    def test_pure_evergreen_high_score(self):
        """순수 에버그린 → 높은 점수"""
        content = (
            '효과적인 의사소통을 위해서는 경청이 중요합니다. '
            '상대방의 말에 집중하고, 공감을 표현하세요.'
        )
        score = get_evergreen_score(content)
        self.assertGreaterEqual(score, 80.0)

    def test_many_signals_low_score(self):
        """만료 신호 많으면 낮은 점수"""
        content = (
            '2024년 3월 iPhone 15 출시. 점유율 78% 기록. '
            '2023년 대비 50% 성장. Galaxy S24 경쟁. '
            'WWDC 2024 발표 내용. Python 3.12 업데이트. '
            '올해 시장 규모 100억원.'
        )
        score = get_evergreen_score(content)
        self.assertLessEqual(score, 50.0)

    def test_score_range_0_to_100(self):
        """점수가 항상 0~100 범위"""
        # 극단적으로 많은 신호
        content = ' '.join([f'2024년 {i}월 통계 {i}%' for i in range(1, 20)])
        score = get_evergreen_score(content)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 100.0)

    def test_severity_weighting(self):
        """high 심각도가 medium보다 더 큰 감점"""
        # high: 날짜 1개
        content_high = '2024년에 발생한 사건.'
        # medium: 버전 1개
        content_medium = 'React 18에서 동작합니다.'
        score_high = get_evergreen_score(content_high)
        score_medium = get_evergreen_score(content_medium)
        # high가 더 큰 감점 → 더 낮은 점수
        self.assertLessEqual(score_high, score_medium)


if __name__ == '__main__':
    unittest.main()
