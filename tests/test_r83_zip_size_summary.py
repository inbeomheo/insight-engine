"""R83: export_zip manifest.json에 총 파일 크기 summary 필드 추가 테스트"""
import io
import json
import zipfile
import unittest

from services.export.export_service import export_zip


class TestZipSizeSummary(unittest.TestCase):
    """ZIP manifest.json의 크기 요약 필드 검증"""

    def _get_manifest(self, title='테스트', content='# 제목\n\n본문 내용입니다.'):
        buf = export_zip(title, content)
        with zipfile.ZipFile(buf) as zf:
            return json.loads(zf.read('manifest.json').decode('utf-8'))

    def test_total_size_bytes_present(self):
        """manifest.json에 total_size_bytes 필드가 존재"""
        manifest = self._get_manifest()
        self.assertIn('total_size_bytes', manifest)
        self.assertIsInstance(manifest['total_size_bytes'], int)
        self.assertGreater(manifest['total_size_bytes'], 0)

    def test_total_compress_size_bytes_present(self):
        """manifest.json에 total_compress_size_bytes 필드가 존재"""
        manifest = self._get_manifest()
        self.assertIn('total_compress_size_bytes', manifest)
        self.assertIsInstance(manifest['total_compress_size_bytes'], int)

    def test_total_size_kb_present(self):
        """manifest.json에 total_size_kb 필드가 존재"""
        manifest = self._get_manifest()
        self.assertIn('total_size_kb', manifest)
        self.assertIsInstance(manifest['total_size_kb'], float)
        self.assertGreater(manifest['total_size_kb'], 0)

    def test_total_size_matches_file_sum(self):
        """total_size_bytes가 개별 파일 크기 합과 일치 (manifest/readme 제외)"""
        manifest = self._get_manifest()
        file_sum = sum(
            f['size_bytes'] for f in manifest['files']
            if f['filename'] not in ('manifest.json', 'readme.txt')
        )
        self.assertEqual(manifest['total_size_bytes'], file_sum)

    def test_existing_fields_preserved(self):
        """기존 필드(version, total_files, files)가 유지"""
        manifest = self._get_manifest()
        self.assertIn('version', manifest)
        self.assertIn('total_files', manifest)
        self.assertIn('files', manifest)


if __name__ == '__main__':
    unittest.main()
