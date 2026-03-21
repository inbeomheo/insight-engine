"""NotebookLM 서비스 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock, call
import json


class TestNotebookLmServiceAuthCheck(unittest.TestCase):
    """인증 상태 확인 테스트"""

    @patch('subprocess.run')
    def test_auth_check_returns_valid_when_authenticated(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='✓ Authentication valid!\n  Profile: default\n  Notebooks found: 15\n  Account: user@gmail.com',
            stderr=''
        )
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)

        result = svc.check_auth()

        self.assertTrue(result['valid'])
        self.assertEqual(result['email'], 'user@gmail.com')

    @patch('subprocess.run')
    def test_auth_check_returns_invalid_when_expired(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='Cookies have expired'
        )
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)

        result = svc.check_auth()

        self.assertFalse(result['valid'])
        self.assertIn('nlm login', result['message'])


class TestNotebookLmServiceNotebook(unittest.TestCase):
    """노트북 생성/재사용 테스트"""

    @patch('subprocess.run')
    def test_ensure_notebook_creates_when_none_exists(self, mock_run):
        """노트북 ID가 없으면 새로 생성한다."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='✓ Created notebook: Insight Engine\n  ID: aaaabbbb-cccc-dddd-eeee-ffffffffffff',
            stderr=''
        )
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': None, 'sources': {}}
        svc._save_state = MagicMock()

        notebook_id = svc._ensure_notebook()

        self.assertEqual(notebook_id, 'aaaabbbb-cccc-dddd-eeee-ffffffffffff')
        self.assertEqual(svc._state['notebook_id'], 'aaaabbbb-cccc-dddd-eeee-ffffffffffff')

    def test_ensure_notebook_reuses_existing(self):
        """노트북 ID가 이미 있으면 재사용한다."""
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': 'existing-id-1234', 'sources': {}}

        notebook_id = svc._ensure_notebook()

        self.assertEqual(notebook_id, 'existing-id-1234')


class TestNotebookLmServiceSource(unittest.TestCase):
    """소스 추가 + 중복 방지 테스트"""

    @patch('subprocess.run')
    def test_add_source_creates_new(self, mock_run):
        """새 URL이면 소스를 추가하고 source_id 반환."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='✓ Added source: 테스트 영상\nSource ID: 11112222-3333-4444-5555-666666666666',
            stderr=''
        )
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': 'nb-id', 'sources': {}}
        svc._save_state = MagicMock()

        source_id = svc._add_source('nb-id', 'https://youtube.com/watch?v=abc', '자막 텍스트')

        self.assertEqual(source_id, '11112222-3333-4444-5555-666666666666')
        self.assertEqual(svc._state['sources']['https://youtube.com/watch?v=abc'], source_id)

    def test_add_source_skips_duplicate(self):
        """이미 추가된 URL이면 CLI를 호출하지 않고 기존 ID 반환."""
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': 'nb-id', 'sources': {
            'https://youtube.com/watch?v=abc': 'existing-source-id'
        }}

        source_id = svc._add_source('nb-id', 'https://youtube.com/watch?v=abc', '자막 텍스트')

        self.assertEqual(source_id, 'existing-source-id')


class TestNotebookLmServiceGenerate(unittest.TestCase):
    """콘텐츠 생성 테스트"""

    @patch('subprocess.run')
    def test_generate_audio_returns_artifact_id(self, mock_run):
        """오디오 생성 요청 시 artifact_id가 반환된다."""
        mock_run.side_effect = [
            # _ensure_notebook (이미 있으므로 호출 안 됨)
            # _add_source
            MagicMock(returncode=0, stdout='✓ Added source: test\nSource ID: aabbccdd-1111-2222-3333-eeeeeeeeeeee', stderr=''),
            # generate (audio create)
            MagicMock(returncode=0, stdout='✓ Audio generation started\n  Artifact ID: a1b2c3d4-1111-2222-3333-555555555555', stderr=''),
        ]
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': 'nb-id', 'sources': {}}
        svc._save_state = MagicMock()

        result = svc.generate('audio', 'https://youtube.com/watch?v=test', '자막 내용')

        self.assertEqual(result['artifact_id'], 'a1b2c3d4-1111-2222-3333-555555555555')
        self.assertEqual(result['status'], 'in_progress')
        self.assertEqual(result['content_type'], 'audio')

    def test_generate_invalid_type_raises(self):
        """지원하지 않는 타입이면 ValueError."""
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': 'nb-id', 'sources': {}}

        with self.assertRaises(ValueError):
            svc.generate('invalid_type', 'url', 'text')


class TestNotebookLmServiceStatus(unittest.TestCase):
    """상태 폴링 테스트"""

    @patch('subprocess.run')
    def test_check_status_returns_completed(self, mock_run):
        """완료된 artifact의 상태를 반환한다."""
        artifacts = [
            {'id': 'art-id-1', 'type': 'audio', 'status': 'completed'},
            {'id': 'art-id-2', 'type': 'video', 'status': 'in_progress'},
        ]
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(artifacts),
            stderr=''
        )
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': 'nb-id', 'sources': {}}

        result = svc.check_status('art-id-1')

        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['type'], 'audio')

    @patch('subprocess.run')
    def test_check_status_returns_in_progress(self, mock_run):
        """진행 중인 artifact의 상태를 반환한다."""
        artifacts = [
            {'id': 'art-id-2', 'type': 'video', 'status': 'in_progress'},
        ]
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(artifacts),
            stderr=''
        )
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': 'nb-id', 'sources': {}}

        result = svc.check_status('art-id-2')

        self.assertEqual(result['status'], 'in_progress')

    @patch('subprocess.run')
    def test_check_status_not_found(self, mock_run):
        """존재하지 않는 artifact_id면 not_found."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='[]',
            stderr=''
        )
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': 'nb-id', 'sources': {}}

        result = svc.check_status('nonexistent-id')

        self.assertEqual(result['status'], 'not_found')


if __name__ == '__main__':
    unittest.main()
