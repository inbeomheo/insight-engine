"""R27: export_zip에 readme.txt 포함 테스트"""
import json
import zipfile
import unittest

from services.export.export_service import export_zip


class TestExportZipReadme(unittest.TestCase):
    """ZIP 내보내기에 readme.txt 포함 여부 검증"""

    def _make_zip(self, title='테스트', content='# 제목\n\n본문 내용입니다.'):
        return export_zip(title, content)

    def test_readme_exists_in_zip(self):
        """readme.txt가 ZIP에 포함되는지 확인"""
        buf = self._make_zip()
        with zipfile.ZipFile(buf) as zf:
            self.assertIn('readme.txt', zf.namelist())

    def test_readme_contains_title(self):
        """readme.txt에 제목이 포함되는지 확인"""
        buf = self._make_zip(title='마이 콘텐츠')
        with zipfile.ZipFile(buf) as zf:
            readme = zf.read('readme.txt').decode('utf-8')
        self.assertIn('마이 콘텐츠', readme)

    def test_readme_contains_char_count(self):
        """readme.txt에 글자 수가 포함되는지 확인"""
        content = '테스트 본문 내용'
        buf = self._make_zip(content=content)
        with zipfile.ZipFile(buf) as zf:
            readme = zf.read('readme.txt').decode('utf-8')
        self.assertIn(f'글자 수: {len(content)}', readme)

    def test_readme_contains_word_count(self):
        """readme.txt에 단어 수가 포함되는지 확인"""
        content = 'hello world test'
        buf = self._make_zip(content=content)
        with zipfile.ZipFile(buf) as zf:
            readme = zf.read('readme.txt').decode('utf-8')
        self.assertIn('단어 수: 3', readme)

    def test_readme_contains_export_timestamp(self):
        """readme.txt에 내보내기 일시가 포함되는지 확인"""
        buf = self._make_zip()
        with zipfile.ZipFile(buf) as zf:
            readme = zf.read('readme.txt').decode('utf-8')
            meta = json.loads(zf.read('meta.json').decode('utf-8'))
        self.assertIn(meta['exported_at'], readme)

    def test_readme_lists_included_files(self):
        """readme.txt에 포함 파일 목록이 나열되는지 확인"""
        buf = self._make_zip(title='테스트')
        with zipfile.ZipFile(buf) as zf:
            readme = zf.read('readme.txt').decode('utf-8')
        self.assertIn('.md', readme)
        self.assertIn('.txt', readme)
        self.assertIn('.docx', readme)
        self.assertIn('meta.json', readme)

    def test_existing_zip_files_still_present(self):
        """readme.txt 추가 후 기존 파일들이 여전히 존재하는지 확인"""
        buf = self._make_zip()
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
        self.assertTrue(any(n.endswith('.md') for n in names))
        self.assertTrue(any(n.endswith('.txt') and n != 'readme.txt' for n in names))
        self.assertTrue(any(n.endswith('.docx') for n in names))
        self.assertIn('meta.json', names)
        self.assertIn('readme.txt', names)


if __name__ == '__main__':
    unittest.main()
