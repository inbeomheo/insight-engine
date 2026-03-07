"""Adverb Overuse Detector 서비스 단위 테스트"""
import unittest
from services.adverb_overuse_service import detect_adverb_overuse


class TestAdverbOveruseService(unittest.TestCase):

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 기본 결과 반환"""
        result = detect_adverb_overuse('')
        self.assertEqual(result['adverbs'], [])
        self.assertEqual(result['summary']['total_adverbs'], 0)
        self.assertEqual(result['score'], 100.0)
        result_none = detect_adverb_overuse(None)
        self.assertEqual(result_none['adverbs'], [])

    def test_no_adverbs(self):
        """부사가 없는 콘텐츠"""
        content = '오늘 날씨가 좋다. 하늘이 파랗다.'
        result = detect_adverb_overuse(content)
        self.assertEqual(result['summary']['total_adverbs'], 0)
        self.assertEqual(result['score'], 100.0)

    def test_korean_adverb_detection(self):
        """한국어 부사 감지"""
        content = '매우 좋은 결과가 나왔다. 정말 빠른 속도다. 아주 큰 변화가 있었다.'
        result = detect_adverb_overuse(content)
        ko_adverbs = [a for a in result['adverbs'] if a['type'] == 'korean']
        self.assertGreaterEqual(len(ko_adverbs), 3)
        names = [a['text'] for a in ko_adverbs]
        self.assertIn('매우', names)
        self.assertIn('정말', names)
        self.assertIn('아주', names)

    def test_english_adverb_detection(self):
        """영어 -ly 부사 감지"""
        content = 'The system quickly processes data. It efficiently handles requests. Additionally it scales automatically.'
        result = detect_adverb_overuse(content)
        en_adverbs = [a for a in result['adverbs'] if a['type'] == 'english_ly']
        self.assertGreaterEqual(len(en_adverbs), 2)
        names = [a['text'] for a in en_adverbs]
        self.assertIn('quickly', names)
        self.assertIn('efficiently', names)

    def test_ly_exception_filter(self):
        """부사가 아닌 -ly 단어 필터링"""
        content = 'The only family member who can apply early is unlikely to reply.'
        result = detect_adverb_overuse(content)
        en_names = [a['text'] for a in result['adverbs'] if a['type'] == 'english_ly']
        for exc in ['only', 'family', 'apply', 'early', 'unlikely', 'reply']:
            self.assertNotIn(exc, en_names)

    def test_weak_combination_korean(self):
        """한국어 약한 부사+동사 조합 감지"""
        content = '이 도구는 매우 좋은 성능을 보여준다.'
        result = detect_adverb_overuse(content)
        self.assertGreater(len(result['weak_combinations']), 0)
        combo = result['weak_combinations'][0]
        self.assertIn('매우 좋', combo['original'])
        self.assertTrue(len(combo['suggestion']) > 0)

    def test_weak_combination_english(self):
        """영어 약한 부사+동사 조합 감지"""
        content = 'This is a very good product with very fast delivery.'
        result = detect_adverb_overuse(content)
        self.assertGreaterEqual(len(result['weak_combinations']), 2)

    def test_adverb_density_calculation(self):
        """부사 밀도 계산 정확성"""
        content = '매우 좋고 정말 빠르며 아주 크다'
        result = detect_adverb_overuse(content)
        self.assertGreater(result['summary']['adverb_density'], 0)
        self.assertIsInstance(result['summary']['adverb_density'], float)

    def test_score_range(self):
        """점수가 0-100 범위 내"""
        # 적은 부사
        r1 = detect_adverb_overuse('간단한 문장이다.')
        self.assertGreaterEqual(r1['score'], 0)
        self.assertLessEqual(r1['score'], 100)
        # 많은 부사
        heavy = ' '.join(['매우 정말 아주 너무 굉장히'] * 10)
        r2 = detect_adverb_overuse(heavy)
        self.assertGreaterEqual(r2['score'], 0)
        self.assertLessEqual(r2['score'], 100)

    def test_high_density_warning(self):
        """높은 밀도 시 경고 제안"""
        content = '매우 정말 아주 너무 굉장히 엄청 상당히 대단히 무척 몹시 꽤 훨씬 가장 더욱 점점'
        result = detect_adverb_overuse(content)
        self.assertTrue(
            any('높습니다' in s or '적정' in s for s in result['suggestions'])
        )

    def test_suggestions_provided(self):
        """제안이 상황에 맞게 생성"""
        content = '매우 좋은 결과. 매우 빠른 속도. 매우 큰 변화.'
        result = detect_adverb_overuse(content)
        self.assertIsInstance(result['suggestions'], list)

    def test_multiple_adverbs(self):
        """동일 부사 반복 횟수 정확"""
        content = '매우 좋고 매우 크고 매우 빠르다.'
        result = detect_adverb_overuse(content)
        mau = [a for a in result['adverbs'] if a['text'] == '매우']
        self.assertEqual(len(mau), 1)
        self.assertEqual(mau[0]['count'], 3)

    def test_return_structure(self):
        """반환값 구조 검증"""
        result = detect_adverb_overuse('매우 좋은 결과다.')
        self.assertIn('adverbs', result)
        self.assertIn('weak_combinations', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_adverbs', result['summary'])
        self.assertIn('adverb_density', result['summary'])
        self.assertIn('weak_combos', result['summary'])


if __name__ == '__main__':
    unittest.main()
