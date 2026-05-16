"""annotation_service 단위 테스트"""
import unittest

from services.content.annotation_service import (
    add_annotation,
    extract_annotations,
    remove_annotations,
    get_annotation_types,
    ANNOTATION_TYPES,
)


class TestAddAnnotation(unittest.TestCase):

    def test_add_at_end(self):
        result = add_annotation('콘텐츠', -1, 'note', '참고사항')
        self.assertIn('<!-- @note: 참고사항 -->', result['annotated'])

    def test_add_at_position(self):
        result = add_annotation('ABCD', 2, 'todo', '할일')
        self.assertIn('<!-- @todo: 할일 -->', result['annotated'])
        self.assertEqual(result['position'], 2)

    def test_invalid_type_defaults_note(self):
        result = add_annotation('콘텐츠', -1, 'invalid', '내용')
        self.assertIn('@note:', result['annotated'])

    def test_empty_content(self):
        result = add_annotation('', -1, 'note', '주석')
        self.assertEqual(result['annotated'], '')

    def test_annotation_id_generated(self):
        result = add_annotation('콘텐츠', 5, 'warn', '경고')
        self.assertIn('warn_', result['annotation_id'])


class TestExtractAnnotations(unittest.TestCase):

    def test_empty_content(self):
        result = extract_annotations('')
        self.assertEqual(result['total'], 0)

    def test_single_annotation(self):
        text = '본문 <!-- @note: 참고사항 --> 텍스트'
        result = extract_annotations(text)
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['annotations'][0]['type'], 'note')
        self.assertEqual(result['annotations'][0]['text'], '참고사항')

    def test_multiple_annotations(self):
        text = '<!-- @note: 참고 --> 본문 <!-- @todo: 할일 --> 끝 <!-- @warn: 경고 -->'
        result = extract_annotations(text)
        self.assertEqual(result['total'], 3)
        types = {a['type'] for a in result['annotations']}
        self.assertEqual(types, {'note', 'todo', 'warn'})

    def test_by_type_counts(self):
        text = '<!-- @note: A --> <!-- @note: B --> <!-- @todo: C -->'
        result = extract_annotations(text)
        self.assertEqual(result['by_type']['note'], 2)
        self.assertEqual(result['by_type']['todo'], 1)

    def test_position_recorded(self):
        text = 'ABC <!-- @note: 주석 --> DEF'
        result = extract_annotations(text)
        self.assertGreater(result['annotations'][0]['position'], 0)

    def test_label_from_type(self):
        text = '<!-- @note: 테스트 -->'
        result = extract_annotations(text)
        self.assertEqual(result['annotations'][0]['label'], '참고')

    def test_no_annotations(self):
        result = extract_annotations('일반 텍스트입니다.')
        self.assertEqual(result['total'], 0)


class TestRemoveAnnotations(unittest.TestCase):

    def test_remove_all(self):
        text = '본문 <!-- @note: 참고 --> 텍스트 <!-- @todo: 할일 -->'
        result = remove_annotations(text)
        self.assertEqual(result['removed_count'], 2)
        self.assertNotIn('<!--', result['cleaned'])

    def test_remove_by_type(self):
        text = '<!-- @note: 참고 --> <!-- @todo: 할일 -->'
        result = remove_annotations(text, annotation_type='note')
        self.assertEqual(result['removed_count'], 1)
        self.assertNotIn('@note', result['cleaned'])
        self.assertIn('@todo', result['cleaned'])

    def test_empty_content(self):
        result = remove_annotations('')
        self.assertEqual(result['removed_count'], 0)

    def test_no_annotations_to_remove(self):
        result = remove_annotations('일반 텍스트')
        self.assertEqual(result['removed_count'], 0)
        self.assertEqual(result['cleaned'], '일반 텍스트')


class TestGetAnnotationTypes(unittest.TestCase):

    def test_returns_all_types(self):
        types = get_annotation_types()
        self.assertEqual(len(types), len(ANNOTATION_TYPES))

    def test_type_structure(self):
        types = get_annotation_types()
        for t in types:
            self.assertIn('id', t)
            self.assertIn('label', t)
            self.assertIn('color', t)


class TestRoundtrip(unittest.TestCase):

    def test_add_then_extract(self):
        original = '원본 콘텐츠입니다.'
        added = add_annotation(original, -1, 'review', '검토 필요')
        extracted = extract_annotations(added['annotated'])
        self.assertEqual(extracted['total'], 1)
        self.assertEqual(extracted['annotations'][0]['text'], '검토 필요')

    def test_add_then_remove(self):
        original = '원본 콘텐츠입니다.'
        added = add_annotation(original, -1, 'note', '참고')
        removed = remove_annotations(added['annotated'])
        self.assertEqual(removed['removed_count'], 1)
        self.assertIn('원본', removed['cleaned'])


if __name__ == '__main__':
    unittest.main()
