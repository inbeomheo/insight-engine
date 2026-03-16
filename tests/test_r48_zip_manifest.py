"""R48: export_zip의 manifest.json 파일 목록 테스트"""
import io
import json
import zipfile
import unittest

from services.export.export_service import export_zip


class TestZipManifest(unittest.TestCase):
    """ZIP 내보내기 manifest.json 검증"""

    def test_manifest_json_exists_in_zip(self):
        """ZIP에 manifest.json이 포함되어야 한다."""
        buf = export_zip('테스트', '# 제목\n본문')
        with zipfile.ZipFile(buf) as zf:
            self.assertIn('manifest.json', zf.namelist())

    def test_manifest_has_version_and_files(self):
        """manifest.json에 version, total_files, files 필드가 있어야 한다."""
        buf = export_zip('매니페스트', '콘텐츠 본문')
        with zipfile.ZipFile(buf) as zf:
            manifest = json.loads(zf.read('manifest.json').decode('utf-8'))

        self.assertIn('version', manifest)
        self.assertIn('total_files', manifest)
        self.assertIn('files', manifest)
        self.assertEqual(manifest['version'], '1.0')

    def test_manifest_lists_all_zip_files(self):
        """manifest의 files 배열이 ZIP 내 모든 파일을 포함해야 한다."""
        buf = export_zip('전체 파일', '# 헤딩\n본문 내용')
        with zipfile.ZipFile(buf) as zf:
            actual_names = set(zf.namelist())
            manifest = json.loads(zf.read('manifest.json').decode('utf-8'))

        manifest_names = {f['filename'] for f in manifest['files']}
        self.assertEqual(actual_names, manifest_names)

    def test_manifest_file_entries_have_size(self):
        """각 파일 항목에 size_bytes, compress_size_bytes가 있어야 한다."""
        buf = export_zip('크기 테스트', '내용')
        with zipfile.ZipFile(buf) as zf:
            manifest = json.loads(zf.read('manifest.json').decode('utf-8'))

        for entry in manifest['files']:
            self.assertIn('filename', entry)
            self.assertIn('size_bytes', entry)
            self.assertIn('compress_size_bytes', entry)

    def test_manifest_total_files_matches(self):
        """total_files가 실제 파일 수와 일치해야 한다."""
        buf = export_zip('카운트', '본문')
        with zipfile.ZipFile(buf) as zf:
            manifest = json.loads(zf.read('manifest.json').decode('utf-8'))
            actual_count = len(zf.namelist())

        self.assertEqual(manifest['total_files'], actual_count)


if __name__ == '__main__':
    unittest.main()
