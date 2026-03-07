"""secret_manager_service 단위 테스트"""
import os
import unittest
from unittest.mock import patch

from services import secret_manager_service


class TestSecretManagerService(unittest.TestCase):

    def setUp(self):
        secret_manager_service.clear_cache()

    def test_cache_hit(self):
        """캐시에 있으면 바로 반환"""
        secret_manager_service._SECRET_CACHE['cached_key'] = 'cached_value'
        result = secret_manager_service.get_secret('cached_key')
        self.assertEqual(result, 'cached_value')

    @patch.dict(os.environ, {'MY_SECRET': 'env_value'})
    def test_env_fallback(self):
        """모든 백엔드 실패 시 환경변수 폴백"""
        result = secret_manager_service.get_secret('nonexistent', env_fallback='MY_SECRET')
        self.assertEqual(result, 'env_value')

    def test_no_secret_returns_empty(self):
        """시크릿 없으면 빈 문자열"""
        result = secret_manager_service.get_secret('nonexistent')
        self.assertEqual(result, '')

    def test_clear_cache(self):
        """캐시 초기화"""
        secret_manager_service._SECRET_CACHE['test'] = 'value'
        secret_manager_service.clear_cache()
        self.assertEqual(len(secret_manager_service._SECRET_CACHE), 0)

    @patch.object(secret_manager_service, '_get_from_aws', return_value='aws_secret')
    def test_aws_provider(self, mock_aws):
        """AWS 백엔드 성공"""
        result = secret_manager_service.get_secret('my_key')
        self.assertEqual(result, 'aws_secret')
        mock_aws.assert_called_once_with('my_key')

    @patch.object(secret_manager_service, '_get_from_aws', return_value=None)
    @patch.object(secret_manager_service, '_get_from_gcp', return_value='gcp_secret')
    def test_gcp_fallback(self, mock_gcp, mock_aws):
        """AWS 실패 → GCP 폴백"""
        result = secret_manager_service.get_secret('my_key')
        self.assertEqual(result, 'gcp_secret')

    @patch.object(secret_manager_service, '_get_from_aws', return_value=None)
    @patch.object(secret_manager_service, '_get_from_gcp', return_value=None)
    @patch.object(secret_manager_service, '_get_from_vault', return_value='vault_secret')
    def test_vault_fallback(self, mock_vault, mock_gcp, mock_aws):
        """AWS/GCP 실패 → Vault 폴백"""
        result = secret_manager_service.get_secret('my_key')
        self.assertEqual(result, 'vault_secret')

    @patch.object(secret_manager_service, '_get_from_aws', return_value='cached_aws')
    def test_result_cached(self, mock_aws):
        """조회 결과가 캐시에 저장됨"""
        secret_manager_service.get_secret('cache_test')
        self.assertEqual(secret_manager_service._SECRET_CACHE['cache_test'], 'cached_aws')

    def test_helper_get_gemini_api_key(self):
        """헬퍼: get_gemini_api_key"""
        secret_manager_service._SECRET_CACHE['GEMINI_API_KEY'] = 'test_gemini'
        self.assertEqual(secret_manager_service.get_gemini_api_key(), 'test_gemini')

    def test_helper_get_deepseek_api_key(self):
        """헬퍼: get_deepseek_api_key"""
        secret_manager_service._SECRET_CACHE['DEEPSEEK_API_KEY'] = 'test_ds'
        self.assertEqual(secret_manager_service.get_deepseek_api_key(), 'test_ds')


if __name__ == '__main__':
    unittest.main()
