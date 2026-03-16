"""R58: /api/export/markdown include_metadata 옵션 테스트"""
from __future__ import annotations

import unittest


class TestExportMarkdownMetadata(unittest.TestCase):
    """export_markdown 함수의 metadata 파라미터 테스트"""

    def test_no_metadata_no_section(self):
        """metadata 미전달 → 생성 정보 섹션 없음"""
        from services.export.export_service import export_markdown

        buf = export_markdown('제목', '본문 내용')
        text = buf.getvalue().decode('utf-8')
        self.assertNotIn('## 생성 정보', text)

    def test_metadata_adds_section(self):
        """metadata 전달 → 하단에 생성 정보 섹션 추가"""
        from services.export.export_service import export_markdown

        metadata = {'model': 'gemini-2.5-flash', 'style': 'blog_seo', 'generated_at': '2026-03-17'}
        buf = export_markdown('제목', '본문', metadata=metadata)
        text = buf.getvalue().decode('utf-8')

        self.assertIn('## 생성 정보', text)
        self.assertIn('**model**: gemini-2.5-flash', text)
        self.assertIn('**style**: blog_seo', text)
        self.assertIn('**generated_at**: 2026-03-17', text)

    def test_metadata_empty_dict_no_section(self):
        """빈 metadata dict → falsy이므로 생성 정보 섹션 없음"""
        from services.export.export_service import export_markdown

        buf = export_markdown('제목', '본문', metadata={})
        text = buf.getvalue().decode('utf-8')
        # Python에서 빈 dict {}는 falsy → if metadata: 통과 안 함
        self.assertNotIn('## 생성 정보', text)

    def test_metadata_with_frontmatter(self):
        """frontmatter + metadata 모두 있을 때 공존"""
        from services.export.export_service import export_markdown

        frontmatter = {'title': '테스트', 'tags': ['AI', '자동화']}
        metadata = {'model': 'deepseek-chat'}
        buf = export_markdown('제목', '본문', frontmatter=frontmatter, metadata=metadata)
        text = buf.getvalue().decode('utf-8')

        self.assertIn('---', text)
        self.assertIn('title: 테스트', text)
        self.assertIn('## 생성 정보', text)
        self.assertIn('**model**: deepseek-chat', text)

    def test_metadata_partial_keys(self):
        """일부 키만 있는 metadata도 정상 처리"""
        from services.export.export_service import export_markdown

        metadata = {'style': 'summary'}
        buf = export_markdown('제목', '본문', metadata=metadata)
        text = buf.getvalue().decode('utf-8')

        self.assertIn('**style**: summary', text)
        self.assertNotIn('**model**', text)


class TestExportMarkdownRouteMetadata(unittest.TestCase):
    """라우트 레벨: include_metadata 옵션 전달 검증"""

    @staticmethod
    def _extract_metadata_from_request(data):
        """라우트에서 사용하는 동일한 metadata 추출 로직"""
        metadata = None
        if data.get('include_metadata'):
            metadata = {}
            for key in ('model', 'style', 'generated_at'):
                val = data.get(key)
                if val:
                    metadata[key] = val
        return metadata if metadata else None

    def test_include_metadata_true_with_fields(self):
        """include_metadata=True + 메타 필드 → metadata dict 반환"""
        data = {
            'include_metadata': True,
            'model': 'gemini-2.5-flash',
            'style': 'blog_seo',
            'generated_at': '2026-03-17T12:00:00',
        }
        result = self._extract_metadata_from_request(data)
        self.assertIsNotNone(result)
        self.assertEqual(result['model'], 'gemini-2.5-flash')
        self.assertEqual(result['style'], 'blog_seo')

    def test_include_metadata_false(self):
        """include_metadata=False → None"""
        data = {'include_metadata': False, 'model': 'test'}
        result = self._extract_metadata_from_request(data)
        self.assertIsNone(result)

    def test_include_metadata_missing(self):
        """include_metadata 없음 → None"""
        data = {'model': 'test'}
        result = self._extract_metadata_from_request(data)
        self.assertIsNone(result)

    def test_include_metadata_no_fields(self):
        """include_metadata=True이나 메타 필드 없음 → None"""
        data = {'include_metadata': True}
        result = self._extract_metadata_from_request(data)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
