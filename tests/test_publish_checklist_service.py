"""publish_checklist_service 단위 테스트"""
import unittest

from services.content.publish_checklist_service import (
    generate_checklist,
    _check_item,
)


class TestGenerateChecklist(unittest.TestCase):

    def test_empty_content(self):
        result = generate_checklist('')
        self.assertFalse(result['ready_to_publish'])
        self.assertEqual(result['score'], 0.0)

    def test_none_content(self):
        result = generate_checklist(None)
        self.assertFalse(result['ready_to_publish'])

    def test_minimal_valid_content(self):
        content = '# 제목\n\n' + '충분한 길이의 콘텐츠입니다. ' * 30
        result = generate_checklist(content, title='좋은 제목입니다')
        self.assertGreater(result['passed_count'], 0)
        self.assertGreater(result['total_count'], 0)

    def test_title_check(self):
        content = '충분한 콘텐츠입니다. ' * 30
        # 제목 있음
        result = generate_checklist(content, title='적절한 제목')
        title_item = next(i for i in result['items'] if i['name'] == 'title')
        self.assertTrue(title_item['passed'])

        # 제목 없음
        result_no = generate_checklist(content, title='')
        title_item_no = next(i for i in result_no['items'] if i['name'] == 'title')
        self.assertFalse(title_item_no['passed'])

    def test_content_length_check(self):
        short = generate_checklist('짧음', title='제목')
        length_item = next(i for i in short['items'] if i['name'] == 'content_length')
        self.assertFalse(length_item['passed'])

        long_content = '충분히 긴 콘텐츠입니다. ' * 30
        result = generate_checklist(long_content, title='제목')
        length_item = next(i for i in result['items'] if i['name'] == 'content_length')
        self.assertTrue(length_item['passed'])

    def test_heading_check(self):
        content = '# 헤딩 있음\n콘텐츠 내용입니다. ' * 20
        result = generate_checklist(content, title='제목')
        heading_item = next(i for i in result['items'] if i['name'] == 'headings')
        self.assertTrue(heading_item['passed'])

    def test_forbidden_words_detected(self):
        content = '이것은 놀라운 혁신적 기술입니다. ' * 20
        result = generate_checklist(content, title='제목')
        forbidden_item = next(i for i in result['items'] if i['name'] == 'forbidden_words')
        self.assertFalse(forbidden_item['passed'])
        self.assertIn('놀라운', forbidden_item['detail'])

    def test_meta_hashtag_thumbnail_flags(self):
        content = '콘텐츠입니다. ' * 30
        result = generate_checklist(content, title='제목', has_meta=True, has_hashtags=True, has_thumbnail=True)
        meta = next(i for i in result['items'] if i['name'] == 'meta_description')
        self.assertTrue(meta['passed'])
        tags = next(i for i in result['items'] if i['name'] == 'hashtags')
        self.assertTrue(tags['passed'])
        thumb = next(i for i in result['items'] if i['name'] == 'thumbnail')
        self.assertTrue(thumb['passed'])

    def test_score_calculation(self):
        content = '# 완벽한 구조\n' + '깨끗한 콘텐츠입니다. ' * 30
        result = generate_checklist(content, title='좋은 제목', has_meta=True, has_hashtags=True, has_thumbnail=True)
        self.assertGreater(result['score'], 0.5)

    def test_formatting_check(self):
        content = '연속  공백이 있는 텍스트입니다. ' * 20
        result = generate_checklist(content, title='제목')
        fmt = next(i for i in result['items'] if i['name'] == 'formatting')
        self.assertFalse(fmt['passed'])

    def test_image_alt_check(self):
        content = '![](img.png) ' + '텍스트. ' * 30
        result = generate_checklist(content, title='제목')
        alt_item = next((i for i in result['items'] if i['name'] == 'image_alt'), None)
        if alt_item:
            self.assertFalse(alt_item['passed'])

    def test_ready_to_publish_threshold(self):
        content = '# 헤딩\n' + '좋은 콘텐츠입니다. ' * 30
        result = generate_checklist(content, title='좋은 제목', has_meta=True, has_hashtags=True, has_thumbnail=True)
        # 대부분 통과하면 ready
        if result['score'] >= 0.7:
            self.assertTrue(result['ready_to_publish'])


class TestCheckItem(unittest.TestCase):

    def test_passed(self):
        item = _check_item('test', '테스트', True, 'OK')
        self.assertTrue(item['passed'])
        self.assertEqual(item['name'], 'test')

    def test_failed(self):
        item = _check_item('test', '테스트', False, '실패')
        self.assertFalse(item['passed'])


if __name__ == '__main__':
    unittest.main()
