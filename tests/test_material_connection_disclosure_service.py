"""Material Connection Disclosure Checker 서비스 테스트."""
import unittest
from services.analysis.material_connection_disclosure_service import check_material_connection_disclosure


class TestMaterialConnectionDisclosure(unittest.TestCase):

    def test_empty_content(self):
        result = check_material_connection_disclosure('')
        self.assertEqual(result['score'], 100.0)
        self.assertFalse(result['summary']['has_material_connection'])

    def test_none_content(self):
        result = check_material_connection_disclosure(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_material_connection(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다. 공원에서 휴식을 취했습니다.'
        result = check_material_connection_disclosure(content)
        self.assertFalse(result['summary']['has_material_connection'])
        self.assertEqual(result['score'], 100.0)

    def test_material_without_disclosure(self):
        content = ('이 제품은 협찬을 받았습니다. 사용해보니 정말 좋았어요. '
                   '강력하게 추천합니다.')
        result = check_material_connection_disclosure(content)
        self.assertTrue(result['summary']['has_material_connection'])
        self.assertLess(result['score'], 100.0)

    def test_material_with_disclosure(self):
        content = ('본 포스팅은 협찬을 받아 작성되었습니다. '
                   '제품을 무료 제공 받았으며 솔직한 리뷰입니다. '
                   '이 제품은 정말 편리합니다.')
        result = check_material_connection_disclosure(content)
        self.assertTrue(result['summary']['disclosure_found'])

    def test_english_affiliate(self):
        content = ('This post contains affiliate links. '
                   'I may earn a commission if you purchase through these links. '
                   'The product was provided for free for review purposes.')
        result = check_material_connection_disclosure(content)
        self.assertTrue(result['summary']['has_material_connection'])

    def test_review_content_detection(self):
        content = ('최고의 노트북 추천 TOP 5 비교 리뷰입니다. '
                   '다양한 제품을 테스트해보았습니다.')
        result = check_material_connection_disclosure(content)
        self.assertTrue(result['summary']['review_content'])

    def test_late_disclosure_placement(self):
        body = '좋은 내용입니다. ' * 50
        content = body + '본 글은 광고를 포함합니다. 협찬 제품 리뷰입니다.'
        result = check_material_connection_disclosure(content)
        self.assertFalse(result['summary']['placement_ok'])

    def test_early_disclosure_placement(self):
        content = ('본 포스팅은 제휴 마케팅을 포함합니다. '
                   '쿠팡 파트너스 활동의 일환으로 수수료를 받습니다. '
                   + '좋은 제품입니다. ' * 20)
        result = check_material_connection_disclosure(content)
        self.assertTrue(result['summary']['has_material_connection'])

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다. 제품 리뷰를 작성합니다.'
        result = check_material_connection_disclosure(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = check_material_connection_disclosure(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('material_markers', result)
        self.assertIn('disclosure_markers', result)
        self.assertIn('suggestions', result)
        self.assertIn('has_material_connection', result['summary'])
        self.assertIn('disclosure_found', result['summary'])
        self.assertIn('review_content', result['summary'])
        self.assertIn('placement_ok', result['summary'])

    def test_hashtag_ad(self):
        content = '이 제품 정말 좋아요! 매일 사용합니다. #ad #협찬'
        result = check_material_connection_disclosure(content)
        self.assertTrue(result['summary']['has_material_connection'])

    def test_suggestions_exist(self):
        content = ('협찬 받은 제품 리뷰입니다. '
                   '정말 좋은 제품이에요. 강력 추천합니다.')
        result = check_material_connection_disclosure(content)
        self.assertGreater(len(result['suggestions']), 0)


class TestMaterialConnectionEdgeCases(unittest.TestCase):

    def test_coupang_partners(self):
        content = '쿠팡 파트너스 활동의 일환으로 수수료를 지급받습니다.'
        result = check_material_connection_disclosure(content)
        self.assertTrue(result['summary']['has_material_connection'])

    def test_experience_group(self):
        content = '체험단으로 선정되어 제품을 무료 제공 받았습니다.'
        result = check_material_connection_disclosure(content)
        self.assertTrue(result['summary']['has_material_connection'])


if __name__ == '__main__':
    unittest.main()
