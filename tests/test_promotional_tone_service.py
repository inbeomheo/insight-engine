"""Promotional Tone Saturation Checker 서비스 테스트"""
import unittest

from services.analysis.promotional_tone_service import check_promotional_tone


class TestPromotionalToneService(unittest.TestCase):
    """check_promotional_tone 함수 테스트 (12개 이상)"""

    # ── 1. 빈 콘텐츠 ──

    def test_empty_content(self):
        """빈 문자열 입력 시 안전한 기본값을 반환한다."""
        result = check_promotional_tone('')
        self.assertEqual(result['detections'], [])
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['summary']['promo_density'], 0.0)
        self.assertEqual(result['hotspots'], [])
        self.assertEqual(result['trust_score'], 100.0)
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'])

        # None 입력도 동일
        result_none = check_promotional_tone(None)
        self.assertEqual(result_none['trust_score'], 100.0)

    # ── 2. 최상급 표현 감지 ──

    def test_superlative_detection(self):
        """최상급(superlative) 표현을 정확히 감지한다."""
        content = '이 제품은 최고의 품질을 자랑합니다. 업계 최초로 출시된 서비스입니다.'
        result = check_promotional_tone(content)

        categories = [d['category'] for d in result['detections']]
        phrases = [d['phrase'] for d in result['detections']]

        self.assertIn('superlative', categories)
        self.assertIn('최고의', phrases)
        self.assertIn('업계 최초', phrases)
        self.assertGreaterEqual(result['summary']['by_category'].get('superlative', 0), 2)

    # ── 3. 과장 표현 감지 ──

    def test_hype_detection(self):
        """과장(hype) 표현을 정확히 감지한다."""
        content = '혁신적인 기술로 놀라운 결과를 만들어 냅니다. 압도적인 성능을 경험하세요.'
        result = check_promotional_tone(content)

        categories = [d['category'] for d in result['detections']]
        phrases = [d['phrase'] for d in result['detections']]

        self.assertIn('hype', categories)
        self.assertIn('혁신적', phrases)
        self.assertIn('놀라운', phrases)
        self.assertIn('압도적', phrases)

    # ── 4. 긴급성 유도 표현 감지 ──

    def test_urgency_detection(self):
        """긴급성(urgency) 유도 표현을 정확히 감지한다."""
        content = '지금 바로 신청하세요. 한정 수량이므로 마감 임박 상태입니다.'
        result = check_promotional_tone(content)

        categories = [d['category'] for d in result['detections']]
        phrases = [d['phrase'] for d in result['detections']]

        self.assertIn('urgency', categories)
        self.assertIn('지금 바로', phrases)
        self.assertIn('한정', phrases)
        self.assertIn('마감 임박', phrases)

    # ── 5. 보장 표현 감지 ──

    def test_guarantee_detection(self):
        """보장(guarantee) 표현을 정확히 감지한다."""
        content = '100% 만족을 보장합니다. 무조건 성공하는 방법을 알려드립니다.'
        result = check_promotional_tone(content)

        categories = [d['category'] for d in result['detections']]
        phrases = [d['phrase'] for d in result['detections']]

        self.assertIn('guarantee', categories)
        self.assertIn('100%', phrases)
        self.assertIn('보장', phrases)
        self.assertIn('무조건', phrases)

    # ── 6. 영향도(impact) 레벨 ──

    def test_impact_levels(self):
        """느낌표/대문자와 함께 사용 시 impact가 상승한다."""
        # 느낌표와 함께 → high
        content_exclaim = '이것은 혁신적인 제품입니다!'
        result = check_promotional_tone(content_exclaim)
        impacts = [d['impact'] for d in result['detections']]
        self.assertIn('high', impacts)

        # 평서문 hype → 기본 high
        content_plain = '이것은 혁신적인 제품입니다.'
        result_plain = check_promotional_tone(content_plain)
        self.assertTrue(
            all(d['impact'] in ('low', 'medium', 'high') for d in result_plain['detections'])
        )

    # ── 7. 신뢰 점수 범위 ──

    def test_trust_score_range(self):
        """trust_score가 항상 0~100 범위이다."""
        # 프로모션 표현이 매우 많은 콘텐츠
        heavy = (
            '최고의 혁신적 놀라운 압도적 게임체인저 보장 무조건 100% '
            '지금 바로 한정 마감 임박 놓치면 서두르세요 확실 최초의 유일한 '
            '혁명적 경이로운 파격적 최상의 최적의 최강 독보적 '
        ) * 5
        result = check_promotional_tone(heavy)
        self.assertGreaterEqual(result['trust_score'], 0.0)
        self.assertLessEqual(result['trust_score'], 100.0)

        # 빈 콘텐츠
        result_empty = check_promotional_tone('')
        self.assertEqual(result_empty['trust_score'], 100.0)

    # ── 8. 프로모션 없는 깨끗한 콘텐츠 ──

    def test_clean_content(self):
        """프로모션 표현이 없는 콘텐츠는 높은 신뢰 점수를 받는다."""
        content = (
            '이 보고서는 2024년 시장 동향을 분석합니다. '
            '조사 방법론은 설문조사와 인터뷰를 병행하였습니다. '
            '데이터에 따르면 전년 대비 15% 성장이 관찰되었습니다.'
        )
        result = check_promotional_tone(content)
        self.assertEqual(result['detections'], [])
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['trust_score'], 100.0)
        self.assertIn('프로모션 표현이 감지되지 않았습니다.', result['suggestions'][0])

    # ── 9. 핫스팟 감지 ──

    def test_hotspot_detection(self):
        """프로모션 표현이 집중된 단락을 핫스팟으로 식별한다."""
        content = (
            '이 보고서는 시장 동향을 분석합니다.\n\n'
            '최고의 혁신적 놀라운 압도적 게임체인저!\n\n'
            '데이터에 따르면 성장이 관찰되었습니다.'
        )
        result = check_promotional_tone(content)

        # 두 번째 단락(index=1)이 핫스팟이어야 함
        self.assertGreater(len(result['hotspots']), 0)
        hotspot_indices = [h['paragraph_index'] for h in result['hotspots']]
        self.assertIn(1, hotspot_indices)

        # 핫스팟에 density와 excerpt가 있어야 함
        for h in result['hotspots']:
            self.assertIn('density', h)
            self.assertIn('excerpt', h)
            self.assertGreater(h['density'], 0)

    # ── 10. 프로모션 밀도 ──

    def test_promo_density(self):
        """promo_density가 올바르게 계산된다."""
        # 단어 수 대비 감지 수의 비율
        content = '이것은 최고의 제품입니다.'
        result = check_promotional_tone(content)
        density = result['summary']['promo_density']

        self.assertIsInstance(density, float)
        self.assertGreater(density, 0.0)
        self.assertLessEqual(density, 1.0)

    # ── 11. 혼합 카테고리 ──

    def test_mixed_categories(self):
        """여러 카테고리가 동시에 감지되고 올바르게 분류된다."""
        content = (
            '최고의 서비스를 지금 바로 체험하세요. '
            '혁신적인 기술로 100% 성공을 보장합니다.'
        )
        result = check_promotional_tone(content)

        detected_cats = set(d['category'] for d in result['detections'])
        # 4개 카테고리 모두 감지되어야 함
        self.assertIn('superlative', detected_cats)
        self.assertIn('urgency', detected_cats)
        self.assertIn('hype', detected_cats)
        self.assertIn('guarantee', detected_cats)

        # by_category에도 반영
        by_cat = result['summary']['by_category']
        self.assertEqual(len(by_cat), 4)

    # ── 12. 개선 제안 ──

    def test_suggestions(self):
        """감지 결과에 따라 적절한 개선 제안이 생성된다."""
        content = (
            '최고의 유일한 서비스입니다. '
            '혁신적인 기술로 놀라운 결과를 냅니다. '
            '지금 바로 신청하세요. '
            '100% 만족을 보장합니다.'
        )
        result = check_promotional_tone(content)

        self.assertGreater(len(result['suggestions']), 0)

        # 각 카테고리별 제안이 포함
        all_suggestions = ' '.join(result['suggestions'])
        self.assertIn('최상급', all_suggestions)
        self.assertIn('과장', all_suggestions)
        self.assertIn('긴급성', all_suggestions)
        self.assertIn('보장', all_suggestions)

    # ── 13. 영어 패턴 감지 ──

    def test_english_pattern_detection(self):
        """영어 프로모션 표현도 정확히 감지한다."""
        content = (
            'This is the best product ever. '
            'It delivers incredible results with a guaranteed outcome. '
            'Act now before it is gone.'
        )
        result = check_promotional_tone(content)

        phrases = [d['phrase'] for d in result['detections']]
        self.assertIn('best', phrases)
        self.assertIn('incredible', phrases)
        self.assertIn('guaranteed', phrases)
        self.assertIn('act now', phrases)

    # ── 14. 감지 항목 구조 검증 ──

    def test_detection_structure(self):
        """각 감지 항목에 필수 필드가 포함되어 있다."""
        content = '혁신적인 제품을 만나보세요.'
        result = check_promotional_tone(content)

        self.assertGreater(len(result['detections']), 0)
        for d in result['detections']:
            self.assertIn('phrase', d)
            self.assertIn('category', d)
            self.assertIn('sentence', d)
            self.assertIn('impact', d)
            self.assertIn(d['impact'], ('low', 'medium', 'high'))
            self.assertIn(d['category'], ('superlative', 'hype', 'urgency', 'guarantee'))


if __name__ == '__main__':
    unittest.main()
