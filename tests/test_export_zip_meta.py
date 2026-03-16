"""R14: export_zip의 meta.json에 generated_at 필드 포함 테스트"""
import io
import json
import zipfile
import unittest
from datetime import datetime

from services.export.export_service import export_zip


class TestExportZipMeta(unittest.TestCase):
    """ZIP 내보내기 meta.json 필드 검증"""

    def test_meta_json_has_generated_at(self):
        """meta.json에 generated_at 필드가 존재하는지 확인"""
        buf = export_zip('테스트 제목', '# 제목\n\n본문 내용입니다.')
        with zipfile.ZipFile(buf) as zf:
            meta_raw = zf.read('meta.json')
            meta = json.loads(meta_raw.decode('utf-8'))

        self.assertIn('generated_at', meta)

    def test_generated_at_is_valid_iso_format(self):
        """generated_at 값이 유효한 ISO 8601 형식인지 확인"""
        buf = export_zip('ISO 테스트', '콘텐츠')
        with zipfile.ZipFile(buf) as zf:
            meta = json.loads(zf.read('meta.json').decode('utf-8'))

        generated_at = meta['generated_at']
        # ISO 8601 파싱 가능 여부 확인
        parsed = datetime.fromisoformat(generated_at)
        self.assertIsInstance(parsed, datetime)

    def test_meta_json_retains_existing_fields(self):
        """기존 필드(title, char_count, exported_at, formats)가 유지되는지 확인"""
        buf = export_zip('기존 필드 테스트', '내용 텍스트')
        with zipfile.ZipFile(buf) as zf:
            meta = json.loads(zf.read('meta.json').decode('utf-8'))

        self.assertEqual(meta['title'], '기존 필드 테스트')
        self.assertIn('char_count', meta)
        self.assertIn('exported_at', meta)
        self.assertIn('formats', meta)
        self.assertIn('generated_at', meta)

    def test_zip_contains_all_files(self):
        """ZIP에 md, txt, docx, meta.json 모두 포함"""
        buf = export_zip('파일 테스트', '# 헤딩\n본문')
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()

        self.assertTrue(any(n.endswith('.md') for n in names))
        self.assertTrue(any(n.endswith('.txt') for n in names))
        self.assertTrue(any(n.endswith('.docx') for n in names))
        self.assertIn('meta.json', names)


if __name__ == '__main__':
    unittest.main()
