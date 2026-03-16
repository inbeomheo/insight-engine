"""R46: /api/version last_commit_message 필드 테스트."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestVersionCommitMessage(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_last_commit_message_field_exists(self, _m):
        """last_commit_message 필드가 응답에 포함된다."""
        resp = self.client.get('/api/version', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('last_commit_message', data)
        self.assertIsInstance(data['last_commit_message'], str)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_last_commit_message_not_empty(self, _m):
        """git 저장소 내에서 실행하면 커밋 메시지가 비어있지 않다."""
        resp = self.client.get('/api/version', headers=_HEADERS)
        data = resp.get_json()
        # git 저장소 안에서 테스트 실행 시 커밋 메시지가 존재
        if data.get('git_hash') != 'unknown':
            self.assertGreater(len(data['last_commit_message']), 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_version_still_has_existing_fields(self, _m):
        """기존 필드들이 여전히 존재한다."""
        resp = self.client.get('/api/version', headers=_HEADERS)
        data = resp.get_json()
        for field in ['name', 'version', 'git_hash', 'git_date', 'services', 'routes', 'python']:
            self.assertIn(field, data)


if __name__ == '__main__':
    unittest.main()
