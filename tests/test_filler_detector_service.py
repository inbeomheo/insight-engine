"""
Filler & Hedge Phrase Detector 서비스 테스트
"""
import unittest
from services.filler_detector_service import detect_fillers


class TestFillerDetectorService(unittest.TestCase):
    """detect_fillers() 함수 단위 테스트 (12개+)"""

    # ── 1. 빈 콘텐츠 ──────────────────────────────────
    def test_empty_content(self):
        """빈 문자열/None 입력 시 빈 결과 반환"""
        for empty in ['', '   ', None]:
            result = detect_fillers(empty)
            self.assertEqual(result['detections'], [])
            self.assertEqual(result['summary']['total_fillers'], 0)
            self.assertEqual(result['summary']['total_hedges'], 0)
            self.assertEqual(result['summary']['clarity_score'], 100.0)

    # ── 2. 한국어 filler 감지 ──────────────────────────
    def test_korean_filler_detection(self):
        """한국어 군더더기 표현을 정확히 감지"""
        content = '사실 이 기능은 기본적으로 매우 중요합니다. 어쨌든 결과는 좋았습니다.'
        result = detect_fillers(content)
        filler_phrases = [d['phrase'] for d in result['detections'] if d['category'] == 'filler']
        self.assertIn('사실', filler_phrases)
        self.assertIn('기본적으로', filler_phrases)
        self.assertIn('어쨌든', filler_phrases)
        self.assertGreaterEqual(result['summary']['total_fillers'], 3)

    # ── 3. 영어 filler 감지 ──────────────────────────
    def test_english_filler_detection(self):
        """영어 군더더기 표현을 정확히 감지"""
        content = 'Basically, this is actually a really important feature. You know, it just works.'
        result = detect_fillers(content)
        filler_phrases = [d['phrase'].lower() for d in result['detections'] if d['category'] == 'filler']
        self.assertIn('basically', filler_phrases)
        self.assertIn('actually', filler_phrases)
        self.assertIn('really', filler_phrases)
        self.assertIn('just', filler_phrases)

    # ── 4. 한국어 hedge 감지 ──────────────────────────
    def test_korean_hedge_detection(self):
        """한국어 헤지(회피/약화) 표현을 감지"""
        content = '이 방법이 아마도 가장 좋을 것 같습니다. 경우에 따라 약간 달라질 수 있습니다.'
        result = detect_fillers(content)
        hedge_phrases = [d['phrase'] for d in result['detections'] if d['category'] == 'hedge']
        self.assertIn('아마도', hedge_phrases)
        self.assertIn('약간', hedge_phrases)
        self.assertIn('경우에 따라', hedge_phrases)
        self.assertGreaterEqual(result['summary']['total_hedges'], 3)

    # ── 5. 영어 hedge 감지 ──────────────────────────
    def test_english_hedge_detection(self):
        """영어 헤지 표현을 감지"""
        content = 'Maybe this could be a solution. It seems to work somewhat effectively. Perhaps we should try.'
        result = detect_fillers(content)
        hedge_phrases = [d['phrase'].lower() for d in result['detections'] if d['category'] == 'hedge']
        self.assertIn('maybe', hedge_phrases)
        self.assertIn('could be', hedge_phrases)
        self.assertIn('seems to', hedge_phrases)
        self.assertIn('somewhat', hedge_phrases)
        self.assertIn('perhaps', hedge_phrases)

    # ── 6. 카테고리 분류 정확성 ──────────────────────
    def test_category_correct(self):
        """filler와 hedge가 올바른 카테고리로 분류"""
        content = '솔직히 이 기능은 어쩌면 불필요할 수 있습니다.'
        result = detect_fillers(content)

        for d in result['detections']:
            if d['phrase'] == '솔직히':
                self.assertEqual(d['category'], 'filler')
            if d['phrase'] == '어쩌면':
                self.assertEqual(d['category'], 'hedge')

    # ── 7. 개선 제안 존재 ──────────────────────────
    def test_suggestion_provided(self):
        """모든 감지 항목에 suggestion이 존재"""
        content = '기본적으로 아마도 이 방법이 좋습니다.'
        result = detect_fillers(content)
        for d in result['detections']:
            self.assertIn('suggestion', d)
            self.assertTrue(len(d['suggestion']) > 0, f'{d["phrase"]}에 suggestion 없음')

    # ── 8. clarity_score 범위 ──────────────────────
    def test_clarity_score_range(self):
        """clarity_score가 항상 0-100 범위"""
        # 깨끗한 텍스트
        clean = detect_fillers('이것은 명확한 문장입니다.')
        self.assertGreaterEqual(clean['summary']['clarity_score'], 0)
        self.assertLessEqual(clean['summary']['clarity_score'], 100)

        # 군더더기 가득한 텍스트
        messy = detect_fillers(
            '사실 기본적으로 솔직히 그냥 진짜 되게 일단 뭐랄까 어쨌든 그러니까 아무튼 어차피 좀.'
        )
        self.assertGreaterEqual(messy['summary']['clarity_score'], 0)
        self.assertLessEqual(messy['summary']['clarity_score'], 100)

    # ── 9. 깨끗한 텍스트 ──────────────────────────
    def test_clean_content(self):
        """군더더기 없는 텍스트는 감지 0건, clarity 높음"""
        content = '데이터 분석 결과를 정리했습니다. 성능이 20% 향상되었습니다.'
        result = detect_fillers(content)
        self.assertEqual(result['summary']['total_fillers'], 0)
        self.assertEqual(result['summary']['total_hedges'], 0)
        self.assertEqual(result['summary']['clarity_score'], 100.0)
        self.assertEqual(result['detections'], [])

    # ── 10. 최악 문장 추출 ──────────────────────────
    def test_worst_sentences(self):
        """filler+hedge가 가장 많은 문장이 worst_sentences에 포함"""
        content = (
            '이것은 깨끗한 문장입니다. '
            '사실 기본적으로 솔직히 이건 나쁜 문장입니다. '
            '결과를 확인하세요.'
        )
        result = detect_fillers(content)
        self.assertGreater(len(result['worst_sentences']), 0)
        # 가장 많은 감지가 있는 문장이 포함되어야 함
        worst = result['worst_sentences'][0]
        self.assertIn('사실', worst)

    # ── 11. filler_ratio 계산 ──────────────────────
    def test_filler_ratio(self):
        """filler_ratio가 올바르게 계산"""
        # 2문장 중 1문장에 filler
        content = '사실 이건 중요합니다. 결과는 정확합니다.'
        result = detect_fillers(content)
        ratio = result['summary']['filler_ratio']
        self.assertGreater(ratio, 0.0)
        self.assertLessEqual(ratio, 1.0)

    # ── 12. 한영 혼합 콘텐츠 ──────────────────────
    def test_mixed_content(self):
        """한영 혼합 텍스트에서 양쪽 모두 감지"""
        content = '사실 이 프로젝트는 basically 성공적이었습니다. Maybe 다음에도 아마도 잘 될 것입니다.'
        result = detect_fillers(content)

        # 한국어 filler
        ko_fillers = [d for d in result['detections']
                      if d['category'] == 'filler' and d['phrase'] == '사실']
        self.assertGreater(len(ko_fillers), 0)

        # 영어 filler
        en_fillers = [d for d in result['detections']
                      if d['category'] == 'filler' and d['phrase'].lower() == 'basically']
        self.assertGreater(len(en_fillers), 0)

        # 한국어 hedge
        ko_hedges = [d for d in result['detections']
                     if d['category'] == 'hedge' and d['phrase'] == '아마도']
        self.assertGreater(len(ko_hedges), 0)

        # 영어 hedge
        en_hedges = [d for d in result['detections']
                     if d['category'] == 'hedge' and d['phrase'].lower() == 'maybe']
        self.assertGreater(len(en_hedges), 0)

    # ── 13. position 값 검증 ──────────────────────
    def test_position_index(self):
        """position이 문장 내 실제 시작 위치를 가리킴"""
        content = '이것은 사실 좋은 방법입니다.'
        result = detect_fillers(content)
        for d in result['detections']:
            if d['phrase'] == '사실':
                # '사실'이 문장에서 실제 위치와 일치하는지
                self.assertEqual(d['sentence'][d['position']:d['position'] + len('사실')], '사실')

    # ── 14. 정규식 기반 한국어 hedge 감지 ─────────
    def test_korean_regex_hedge(self):
        """'~인 것 같다', '~일 수도' 등 정규식 패턴 감지"""
        content = '이 방법이 좋은 것 같습니다. 성능이 떨어질 수도 있습니다.'
        result = detect_fillers(content)
        hedge_phrases = [d['phrase'] for d in result['detections'] if d['category'] == 'hedge']
        # 정규식 패턴이 최소 1개 매칭
        self.assertGreater(len(hedge_phrases), 0)

    # ── 15. suggestions 필드 검증 ─────────────────
    def test_suggestions_content(self):
        """감지 결과에 따라 적절한 suggestions 생성"""
        # filler 포함
        result_f = detect_fillers('사실 이것은 중요합니다.')
        self.assertTrue(any('군더더기' in s for s in result_f['suggestions']))

        # hedge 포함
        result_h = detect_fillers('아마도 이것이 답입니다.')
        self.assertTrue(any('헤지' in s for s in result_h['suggestions']))

        # 깨끗한 텍스트
        result_c = detect_fillers('명확한 결론입니다.')
        self.assertTrue(any('깔끔' in s for s in result_c['suggestions']))


if __name__ == '__main__':
    unittest.main()
