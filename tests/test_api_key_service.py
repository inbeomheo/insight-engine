"""api_key_service 단위 테스트"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from services.api_key_service import (
    _generate_api_key,
    _hash_key,
    _mask_key,
    _load_local,
    _save_local,
    ApiKeyService,
)


class TestGenerateApiKey(unittest.TestCase):

    def test_prefix(self):
        """ie_ 접두사"""
        key = _generate_api_key()
        self.assertTrue(key.startswith('ie_'))

    def test_length(self):
        """키 길이 충분"""
        key = _generate_api_key()
        self.assertGreater(len(key), 30)

    def test_unique(self):
        """매번 다른 키"""
        keys = {_generate_api_key() for _ in range(10)}
        self.assertEqual(len(keys), 10)


class TestHashKey(unittest.TestCase):

    def test_sha256_hex(self):
        """SHA256 해시 형식"""
        h = _hash_key('ie_test_key')
        self.assertEqual(len(h), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in h))

    def test_deterministic(self):
        """동일 입력 → 동일 해시"""
        self.assertEqual(_hash_key('abc'), _hash_key('abc'))

    def test_different_input(self):
        """다른 입력 → 다른 해시"""
        self.assertNotEqual(_hash_key('abc'), _hash_key('def'))


class TestMaskKey(unittest.TestCase):

    def test_long_key(self):
        """긴 키 → 앞7 + ... + 뒤4"""
        result = _mask_key('ie_abcdefghijklmnop')
        self.assertEqual(result, 'ie_abcd...mnop')

    def test_short_key(self):
        """짧은 키 → ****"""
        result = _mask_key('short')
        self.assertEqual(result, '****')

    def test_exactly_10(self):
        """정확히 10자 → ****"""
        result = _mask_key('1234567890')
        self.assertEqual(result, '****')


class TestLocalStorage(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmp_file = os.path.join(self.tmpdir, 'keys.json')

    def tearDown(self):
        if os.path.exists(self.tmp_file):
            os.remove(self.tmp_file)
        os.rmdir(self.tmpdir)

    @patch('services.api_key_service._LOCAL_API_KEYS_FILE')
    def test_load_nonexistent(self, mock_path):
        """파일 없음 → 빈 dict"""
        mock_path.__str__ = lambda s: '/nonexistent/path.json'
        with patch('services.api_key_service.os.path.exists', return_value=False):
            result = _load_local()
        self.assertEqual(result, {})

    def test_save_and_load(self):
        """저장 후 로드"""
        test_data = {'user1': [{'name': 'key1'}]}
        with patch('services.api_key_service._LOCAL_API_KEYS_FILE', self.tmp_file):
            _save_local(test_data)
            result = _load_local()
        self.assertEqual(result, test_data)


class TestApiKeyServiceLocal(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmp_file = os.path.join(self.tmpdir, 'keys.json')
        self.patcher_file = patch('services.api_key_service._LOCAL_API_KEYS_FILE', self.tmp_file)
        self.patcher_supabase = patch('services.api_key_service.is_supabase_enabled', return_value=False)
        self.patcher_file.start()
        self.patcher_supabase.start()

    def tearDown(self):
        self.patcher_file.stop()
        self.patcher_supabase.stop()
        if os.path.exists(self.tmp_file):
            os.remove(self.tmp_file)
        os.rmdir(self.tmpdir)

    def test_create_key(self):
        """키 생성 → ie_ 접두사 키 반환"""
        result = ApiKeyService.create_key('user1', 'my-key')
        self.assertTrue(result['key'].startswith('ie_'))
        self.assertEqual(result['name'], 'my-key')
        self.assertIn('key_id', result)

    def test_list_keys(self):
        """생성 후 목록 조회"""
        ApiKeyService.create_key('user1', 'test-key')
        keys = ApiKeyService.list_keys('user1')
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]['name'], 'test-key')
        self.assertIn('...', keys[0]['key_preview'])

    def test_revoke_key(self):
        """키 비활성화"""
        created = ApiKeyService.create_key('user1', 'to-revoke')
        result = ApiKeyService.revoke_key('user1', created['key_id'])
        self.assertTrue(result)
        # 비활성화 후 목록에서 제외
        keys = ApiKeyService.list_keys('user1')
        self.assertEqual(len(keys), 0)

    def test_revoke_nonexistent(self):
        """존재하지 않는 키 비활성화 → False"""
        result = ApiKeyService.revoke_key('user1', 'nonexistent')
        self.assertFalse(result)

    def test_validate_key(self):
        """키 검증 성공"""
        created = ApiKeyService.create_key('user1', 'valid-key')
        result = ApiKeyService.validate_key(created['key'])
        self.assertIsNotNone(result)
        self.assertEqual(result['user_id'], 'user1')

    def test_validate_invalid_key(self):
        """잘못된 키 → None"""
        result = ApiKeyService.validate_key('ie_invalid_key_12345')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
