"""
Information Gain Analyzer 서비스 테스트
"""
import unittest
from services.analysis.information_gain_service import analyze_information_gain


class TestInformationGainService(unittest.TestCase):
    """정보 이득 분석 서비스 테스트"""

    # --- 빈 콘텐츠 ---

    def test_empty_content(self):
        """빈 콘텐츠는 F등급과 빈 신호를 반환해야 한다."""
        result = analyze_information_gain('')
        self.assertEqual(result['grade'], 'F')
        self.assertEqual(result['information_gain_score'], 0.0)
        self.assertIsNone(result['differentiation_score'])
        for signal in result['signals'].values():
            self.assertEqual(signal['count'], 0)
            self.assertEqual(signal['items'], [])
        # 모든 영역이 weak_areas에 포함
        self.assertEqual(len(result['weak_areas']), 5)

    def test_none_content(self):
        """None 입력도 빈 콘텐츠와 동일하게 처리해야 한다."""
        result = analyze_information_gain(None)
        self.assertEqual(result['grade'], 'F')
        self.assertEqual(result['information_gain_score'], 0.0)

    # --- 개별 신호 감지 ---

    def test_unique_data_detection(self):
        """수치/통계 데이터를 감지해야 한다."""
        content = '이 서비스의 사용자 만족도는 95%이며, 월간 활성 사용자가 약 150만 명에 달합니다. 처리 속도는 0.3초입니다.'
        result = analyze_information_gain(content)
        signal = result['signals']['unique_data']
        self.assertGreaterEqual(signal['count'], 2)
        self.assertTrue(len(signal['items']) >= 2)

    def test_example_detection(self):
        """사례/예시 패턴을 감지해야 한다."""
        content = '예를 들어 구글은 검색 알고리즘을 매년 업데이트합니다. 실제로 2023년에는 큰 변화가 있었습니다. 사례: 네이버 블로그 최적화.'
        result = analyze_information_gain(content)
        signal = result['signals']['examples']
        self.assertGreaterEqual(signal['count'], 2)

    def test_counterpoint_detection(self):
        """반론/반례 패턴을 감지해야 한다."""
        content = '이 방법은 효과적입니다. 하지만 모든 상황에 적용할 수는 없습니다. 반면 전통적 방법은 안정적입니다. 다만 속도에서 한계가 있습니다.'
        result = analyze_information_gain(content)
        signal = result['signals']['counterpoints']
        self.assertGreaterEqual(signal['count'], 3)

    def test_original_insight_detection(self):
        """독자적 관점 패턴을 감지해야 한다."""
        content = '필자는 이 기술을 3년간 사용해왔습니다. 우리 팀에서 직접 테스트한 결과, 생산성이 크게 향상되었습니다. 제 경험상 초기 설정이 중요합니다.'
        result = analyze_information_gain(content)
        signal = result['signals']['original_insights']
        self.assertGreaterEqual(signal['count'], 3)

    def test_actionable_tip_detection(self):
        """실행 가능한 팁 패턴을 감지해야 한다."""
        content = '먼저 환경을 설정하세요. 그 다음 테스트를 실행해보세요. 팁: 캐시를 미리 비워두면 좋습니다. 매일 백업하는 것이 좋습니다.'
        result = analyze_information_gain(content)
        signal = result['signals']['actionable_tips']
        self.assertGreaterEqual(signal['count'], 2)

    # --- 점수 및 등급 ---

    def test_score_range(self):
        """점수는 0-100 범위여야 한다."""
        # 빈 콘텐츠
        result_empty = analyze_information_gain('')
        self.assertGreaterEqual(result_empty['information_gain_score'], 0)
        self.assertLessEqual(result_empty['information_gain_score'], 100)

        # 풍부한 콘텐츠
        rich = (
            '사용자 만족도는 95%입니다. 월 150만 명이 사용합니다. '
            '예를 들어 구글의 사례가 있습니다. 실제로 적용해보았습니다. '
            '하지만 한계도 있습니다. 반면 다른 접근법도 존재합니다. '
            '필자는 직접 테스트했습니다. 우리 팀의 실험 결과입니다. '
            '먼저 설정하세요. 팁: 캐시를 비우세요.'
        )
        result_rich = analyze_information_gain(rich)
        self.assertGreaterEqual(result_rich['information_gain_score'], 0)
        self.assertLessEqual(result_rich['information_gain_score'], 100)

    def test_grade_assignment(self):
        """점수에 따라 올바른 등급이 부여되어야 한다."""
        # 빈 콘텐츠 → F
        result_f = analyze_information_gain('')
        self.assertEqual(result_f['grade'], 'F')

        # 다양한 신호가 포함된 콘텐츠 → D 이상
        moderate = (
            '이 방법은 30% 더 효율적입니다. 처리량은 약 500건입니다. '
            '예를 들어 A사의 사례가 있습니다. 실제로 도입 후 개선되었습니다. '
            '하지만 비용이 높습니다. 반면 기존 방식도 장점이 있습니다. '
            '필자는 직접 테스트했습니다. '
            '먼저 환경을 설정하세요.'
        )
        result_mod = analyze_information_gain(moderate)
        self.assertIn(result_mod['grade'], ['A', 'B', 'C', 'D'])

    # --- 레퍼런스 비교 ---

    def test_with_reference(self):
        """레퍼런스 콘텐츠 대비 차별화 점수를 계산해야 한다."""
        content = '파이썬은 데이터 분석에 강력한 언어입니다. 머신러닝 라이브러리가 풍부합니다.'
        references = [
            '파이썬은 프로그래밍 언어입니다. 웹 개발에도 사용됩니다.',
            '자바스크립트는 프론트엔드 개발에 널리 사용됩니다.',
        ]
        result = analyze_information_gain(content, reference_contents=references)
        self.assertIsNotNone(result['differentiation_score'])
        self.assertGreaterEqual(result['differentiation_score'], 0)
        self.assertLessEqual(result['differentiation_score'], 100)

    def test_without_reference(self):
        """레퍼런스가 없으면 differentiation_score는 None이어야 한다."""
        content = '파이썬은 강력한 프로그래밍 언어입니다.'
        result = analyze_information_gain(content)
        self.assertIsNone(result['differentiation_score'])

        # 빈 리스트도 동일
        result2 = analyze_information_gain(content, reference_contents=[])
        self.assertIsNone(result2['differentiation_score'])

    # --- 부족 영역 ---

    def test_weak_areas(self):
        """신호가 부족한 영역을 감지해야 한다."""
        # 수치 데이터만 있는 콘텐츠
        content = '매출은 200억 원이며 성장률은 15%입니다.'
        result = analyze_information_gain(content)
        # unique_data는 있지만 나머지는 부족
        self.assertNotIn('unique_data', result['weak_areas'])
        self.assertIn('examples', result['weak_areas'])
        self.assertIn('counterpoints', result['weak_areas'])
        self.assertIn('original_insights', result['weak_areas'])
        self.assertIn('actionable_tips', result['weak_areas'])

    # --- 풍부한 콘텐츠 ---

    def test_rich_content(self):
        """모든 신호가 포함된 콘텐츠는 높은 점수와 A/B 등급을 받아야 한다."""
        content = (
            '이 프레임워크의 성능은 기존 대비 40% 향상되었습니다. '
            '응답 시간은 평균 0.5초이며 처리량은 초당 1000건입니다. '
            '동시접속자는 약 5000명을 지원합니다. 가용성은 99.9%입니다. '
            '예를 들어 대형 이커머스 사이트에서 도입한 사례가 있습니다. '
            '실제로 도입 후 매출이 25% 증가했습니다. '
            '사례: 글로벌 기업의 마이그레이션 프로젝트입니다. '
            '하지만 초기 학습 비용이 높다는 단점이 있습니다. '
            '반면 기존 솔루션은 안정성이 검증되어 있습니다. '
            '다만 확장성에서 한계가 명확합니다. '
            '필자는 2년간 프로덕션 환경에서 운영해왔습니다. '
            '우리 팀에서 직접 테스트한 결과 안정성을 확인했습니다. '
            '제 경험상 모니터링 설정이 핵심입니다. '
            '먼저 개발 환경을 구성하세요. 의존성을 먼저 확인해보세요. '
            '팁: 캐시 전략을 미리 수립하면 성능이 크게 개선됩니다. '
            '체크리스트를 만들어 배포 전 점검하는 것이 좋습니다.'
        )
        result = analyze_information_gain(content)

        # 높은 점수
        self.assertGreaterEqual(result['information_gain_score'], 60)

        # A 또는 B 등급
        self.assertIn(result['grade'], ['A', 'B'])

        # 모든 신호에서 최소 1개 이상 감지
        for signal_name, signal_data in result['signals'].items():
            self.assertGreaterEqual(
                signal_data['count'], 1,
                f'{signal_name} 신호가 감지되지 않았습니다.'
            )

        # 부족 영역 없음
        self.assertEqual(len(result['weak_areas']), 0)

    # --- 반환 구조 검증 ---

    def test_return_structure(self):
        """반환값의 구조가 명세와 일치해야 한다."""
        content = '간단한 테스트 콘텐츠입니다.'
        result = analyze_information_gain(content)

        # 최상위 키 확인
        required_keys = {'signals', 'information_gain_score', 'differentiation_score', 'grade', 'weak_areas', 'suggestions'}
        self.assertEqual(set(result.keys()), required_keys)

        # signals 구조 확인
        expected_signals = {'unique_data', 'examples', 'counterpoints', 'original_insights', 'actionable_tips'}
        self.assertEqual(set(result['signals'].keys()), expected_signals)

        for signal_data in result['signals'].values():
            self.assertIn('count', signal_data)
            self.assertIn('items', signal_data)
            self.assertIsInstance(signal_data['count'], int)
            self.assertIsInstance(signal_data['items'], list)

        # 타입 확인
        self.assertIsInstance(result['information_gain_score'], float)
        self.assertIsInstance(result['grade'], str)
        self.assertIsInstance(result['weak_areas'], list)
        self.assertIsInstance(result['suggestions'], list)

    def test_identical_reference_low_differentiation(self):
        """동일한 레퍼런스와 비교하면 차별화 점수가 낮아야 한다."""
        content = '파이썬은 강력한 프로그래밍 언어입니다. 데이터 분석에 적합합니다.'
        references = [content]  # 동일 콘텐츠
        result = analyze_information_gain(content, reference_contents=references)
        self.assertIsNotNone(result['differentiation_score'])
        # 동일 콘텐츠이므로 차별화 점수 0
        self.assertEqual(result['differentiation_score'], 0.0)


if __name__ == '__main__':
    unittest.main()
