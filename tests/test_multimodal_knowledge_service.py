"""멀티모달 지식 서비스 테스트"""
import unittest
from services.multimodal_knowledge_service import (
    KnowledgeItem, KnowledgeBase,
    add_item, search_by_tags, cross_modal_link, get_statistics,
)


class TestAddItem(unittest.TestCase):
    """지식 항목 추가 테스트"""

    def setUp(self):
        self.kb = KnowledgeBase(kb_id='kb1', items=[], index={})

    def test_add_text(self):
        result = add_item(self.kb, 'text', '텍스트 콘텐츠', tags=['태그1'])
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].modality, 'text')
        self.assertEqual(result.items[0].content, '텍스트 콘텐츠')

    def test_add_image(self):
        result = add_item(self.kb, 'image', 'image_path.png',
                          metadata={'width': 800, 'height': 600})
        self.assertEqual(result.items[0].modality, 'image')

    def test_add_audio(self):
        result = add_item(self.kb, 'audio', 'audio.mp3')
        self.assertEqual(result.items[0].modality, 'audio')

    def test_add_video(self):
        result = add_item(self.kb, 'video', 'video.mp4')
        self.assertEqual(result.items[0].modality, 'video')

    def test_invalid_modality(self):
        with self.assertRaises(ValueError):
            add_item(self.kb, 'invalid', '내용')

    def test_index_updated(self):
        """인덱스 업데이트 확인"""
        result = add_item(self.kb, 'text', '내용', tags=['AI', '머신러닝'])
        self.assertIn('ai', result.index)
        self.assertIn('머신러닝', result.index)

    def test_created_at_set(self):
        result = add_item(self.kb, 'text', '내용')
        self.assertTrue(len(result.items[0].created_at) > 0)

    def test_multiple_items(self):
        kb = add_item(self.kb, 'text', '텍스트', tags=['태그'])
        kb = add_item(kb, 'image', '이미지', tags=['태그'])
        self.assertEqual(len(kb.items), 2)
        self.assertEqual(len(kb.index['태그']), 2)


class TestSearchByTags(unittest.TestCase):
    """태그 검색 테스트"""

    def setUp(self):
        kb = KnowledgeBase(kb_id='kb1', items=[], index={})
        kb = add_item(kb, 'text', '파이썬 기초', tags=['프로그래밍', 'AI'])
        kb = add_item(kb, 'image', '도표', tags=['AI', '시각화'])
        kb = add_item(kb, 'audio', '강의', tags=['프로그래밍'])
        self.kb = kb

    def test_and_mode(self):
        """AND 모드: 모든 태그 일치"""
        results = search_by_tags(self.kb, ['프로그래밍', 'AI'], match_mode='AND')
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, '파이썬 기초')

    def test_or_mode(self):
        """OR 모드: 하나 이상 일치"""
        results = search_by_tags(self.kb, ['프로그래밍', 'AI'], match_mode='OR')
        self.assertEqual(len(results), 3)

    def test_no_match(self):
        results = search_by_tags(self.kb, ['존재안함'], match_mode='AND')
        self.assertEqual(len(results), 0)

    def test_empty_tags(self):
        """빈 태그 → 전체 반환"""
        results = search_by_tags(self.kb, [])
        self.assertEqual(len(results), 3)

    def test_case_insensitive(self):
        """대소문자 무시"""
        results = search_by_tags(self.kb, ['ai'], match_mode='AND')
        self.assertEqual(len(results), 2)

    def test_single_tag(self):
        results = search_by_tags(self.kb, ['시각화'], match_mode='AND')
        self.assertEqual(len(results), 1)


class TestCrossModalLink(unittest.TestCase):
    """크로스모달 연결 테스트"""

    def setUp(self):
        kb = KnowledgeBase(kb_id='kb1', items=[], index={})
        kb = add_item(kb, 'text', '텍스트 내용', tags=['태그'])
        kb = add_item(kb, 'image', '이미지 설명', tags=['태그'])
        self.kb = kb
        self.text_id = kb.items[0].item_id
        self.image_id = kb.items[1].item_id

    def test_cross_modal(self):
        """다른 모달리티 간 연결"""
        link = cross_modal_link(self.kb, self.text_id, self.image_id, 'illustrates')
        self.assertTrue(link['is_cross_modal'])
        self.assertEqual(link['modality_a'], 'text')
        self.assertEqual(link['modality_b'], 'image')
        self.assertEqual(link['relation'], 'illustrates')

    def test_same_modal(self):
        """같은 모달리티 간 연결"""
        kb = add_item(self.kb, 'text', '두 번째 텍스트')
        text2_id = kb.items[2].item_id
        link = cross_modal_link(kb, self.text_id, text2_id)
        self.assertFalse(link['is_cross_modal'])

    def test_invalid_id(self):
        with self.assertRaises(ValueError):
            cross_modal_link(self.kb, 'nonexistent', self.image_id)

    def test_link_id_generated(self):
        link = cross_modal_link(self.kb, self.text_id, self.image_id)
        self.assertTrue(len(link['link_id']) > 0)


class TestGetStatistics(unittest.TestCase):
    """통계 조회 테스트"""

    def test_basic_stats(self):
        kb = KnowledgeBase(kb_id='kb1', items=[], index={})
        kb = add_item(kb, 'text', 'T1', tags=['AI'])
        kb = add_item(kb, 'text', 'T2', tags=['AI'])
        kb = add_item(kb, 'image', 'I1', tags=['시각화'])

        stats = get_statistics(kb)
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['by_modality']['text'], 2)
        self.assertEqual(stats['by_modality']['image'], 1)
        self.assertEqual(stats['tag_count'], 2)

    def test_empty_kb(self):
        kb = KnowledgeBase(kb_id='kb1', items=[], index={})
        stats = get_statistics(kb)
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['by_modality'], {})

    def test_unique_tags(self):
        kb = KnowledgeBase(kb_id='kb1', items=[], index={})
        kb = add_item(kb, 'text', 'T1', tags=['AI', 'ML'])
        kb = add_item(kb, 'text', 'T2', tags=['AI', 'DL'])

        stats = get_statistics(kb)
        self.assertEqual(stats['tag_count'], 3)  # ai, ml, dl
        self.assertIn('ai', stats['unique_tags'])


if __name__ == '__main__':
    unittest.main()
