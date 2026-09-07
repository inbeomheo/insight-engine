"""NotebookLM 서비스 단위 테스트"""
from contextlib import contextmanager
import json
import multiprocessing
import os
import stat
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch


def _concurrent_state_writer(
    state_path,
    user_id,
    notebook_id,
    source_url,
    source_id,
    artifact_id,
    ready_queue,
    start_event,
):
    """동일한 초기 상태를 읽은 후 동시 저장하는 프로세스 worker."""
    from services.notebooklm import notebooklm_service as service_module

    service_module.STATE_FILE = state_path
    service = service_module.NotebookLmService()
    state_patch = {
        'notebook_id': notebook_id,
        'sources': {source_url: source_id},
        'artifacts': {
            artifact_id: {
                'notebook_id': notebook_id,
                'source_id': source_id,
                'content_type': 'audio',
            },
        },
    }
    ready_queue.put(os.getpid())
    if not start_event.wait(timeout=15):
        raise RuntimeError('동시 저장 시작 신호를 받지 못했습니다.')
    service._save_state(user_id, state_patch)


def _probe_file_lock(lock_path, result_queue):
    """다른 프로세스의 파일 잠금을 비차단 방식으로 확인한다."""
    import fcntl

    with open(os.path.abspath(lock_path), 'a+b') as lock_file:
        try:
            fcntl.flock(
                lock_file.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
        except BlockingIOError:
            result_queue.put(False)
            return

        result_queue.put(True)
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


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
        self.assertEqual(
            svc._state['artifacts'][result['artifact_id']]['notebook_id'],
            'nb-id',
        )

    def test_generate_invalid_type_raises(self):
        """지원하지 않는 타입이면 ValueError."""
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': 'nb-id', 'sources': {}}
        on_cost_start = MagicMock()

        with self.assertRaises(ValueError):
            svc.generate(
                'invalid_type',
                'url',
                'text',
                on_cost_start=on_cost_start,
            )

        on_cost_start.assert_not_called()

    def test_generate_marks_cost_immediately_before_each_new_cli_mutation(self):
        """새 노트북·소스·artifact CLI 직전에 각각 비용을 확정한다."""
        from services.notebooklm.notebooklm_service import NotebookLmService

        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': None, 'sources': {}, 'artifacts': {}}
        svc._save_state = MagicMock()
        events = []

        def run_nlm(args, timeout=60):
            events.append(f'cli:{args[0]}')
            if args[:2] == ['notebook', 'create']:
                stdout = 'ID: aaaabbbb-cccc-dddd-eeee-ffffffffffff'
            elif args[:2] == ['source', 'add']:
                stdout = 'Source ID: 11112222-3333-4444-5555-666666666666'
            else:
                stdout = 'Artifact ID: a1b2c3d4-1111-2222-3333-555555555555'
            return MagicMock(returncode=0, stdout=stdout, stderr='')

        svc._run_nlm = MagicMock(side_effect=run_nlm)

        svc.generate(
            'audio',
            'https://youtube.com/watch?v=test',
            '자막',
            on_cost_start=lambda: events.append('callback'),
        )

        self.assertEqual(events, [
            'callback',
            'cli:notebook',
            'callback',
            'cli:source',
            'callback',
            'cli:audio',
        ])

    def test_generate_reused_notebook_and_source_only_marks_artifact(self):
        """이미 있는 노트북과 소스는 비용 콜백을 추가로 호출하지 않는다."""
        from services.notebooklm.notebooklm_service import NotebookLmService

        url = 'https://youtube.com/watch?v=test'
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {
            'notebook_id': 'existing-notebook',
            'sources': {url: 'existing-source'},
            'artifacts': {},
        }
        svc._save_state = MagicMock()
        on_cost_start = MagicMock()
        svc._run_nlm = MagicMock(return_value=MagicMock(
            returncode=0,
            stdout='Artifact ID: a1b2c3d4-1111-2222-3333-555555555555',
            stderr='',
        ))

        svc.generate(
            'audio',
            url,
            '자막',
            on_cost_start=on_cost_start,
        )

        on_cost_start.assert_called_once_with()
        svc._run_nlm.assert_called_once()
        self.assertEqual(svc._run_nlm.call_args.args[0][0:2], ['audio', 'create'])


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

    @patch('subprocess.run')
    def test_check_status_does_not_expose_cli_stderr(self, mock_run):
        """CLI 내부 오류나 계정 정보는 API 응답에 노출하지 않는다."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='token=secret-value /home/private-user/.config/nlm',
        )
        from services.notebooklm.notebooklm_service import NotebookLmService
        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {'notebook_id': 'nb-id', 'sources': {}}

        result = svc.check_status('art-id-1')

        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['error'], 'NotebookLM 상태를 확인하지 못했습니다.')
        self.assertNotIn('secret-value', result['error'])


class TestNotebookLmServiceUserIsolation(unittest.TestCase):
    """사용자별 네임스페이스와 artifact 소유권 테스트."""

    def _service(self):
        from services.notebooklm.notebooklm_service import NotebookLmService

        svc = NotebookLmService.__new__(NotebookLmService)
        svc._state = {
            'notebook_id': None,
            'sources': {},
            'artifacts': {},
            'users': {
                'user-a': {
                    'notebook_id': 'notebook-a',
                    'sources': {'url-a': 'source-a'},
                    'artifacts': {
                        'artifact-a': {
                            'notebook_id': 'notebook-a',
                            'source_id': 'source-a',
                            'content_type': 'audio',
                        },
                    },
                },
                'user-b': {
                    'notebook_id': 'notebook-b',
                    'sources': {},
                    'artifacts': {},
                },
            },
        }
        return svc

    def test_notebook_and_sources_are_namespaced_by_user(self):
        svc = self._service()

        self.assertEqual(svc._ensure_notebook('user-a'), 'notebook-a')
        self.assertEqual(svc._ensure_notebook('user-b'), 'notebook-b')
        self.assertEqual(
            svc._add_source('notebook-a', 'url-a', 'text', 'user-a'),
            'source-a',
        )
        self.assertNotIn('url-a', svc._state['users']['user-b']['sources'])

    def test_status_rejects_artifact_owned_by_another_user(self):
        svc = self._service()
        svc._run_nlm = MagicMock()

        result = svc.check_status('artifact-a', user_id='user-b')

        self.assertEqual(result['status'], 'not_found')
        svc._run_nlm.assert_not_called()

    def test_download_passes_exact_artifact_id_to_cli(self):
        svc = self._service()
        svc.check_status = MagicMock(return_value={'status': 'completed', 'type': 'audio'})
        svc._run_nlm = MagicMock(return_value=MagicMock(returncode=0, stderr=''))

        path = svc.download('artifact-a', output_dir='/tmp', user_id='user-a')

        self.assertEqual(path, '/tmp/artifact-a.mp3')
        svc._run_nlm.assert_called_once_with(
            [
                'download',
                'audio',
                'notebook-a',
                'artifact-a',
                '--output',
                '/tmp/artifact-a.mp3',
            ],
            timeout=120,
        )

    def test_download_rejects_artifact_owned_by_another_user(self):
        from services.notebooklm.notebooklm_service import ARTIFACT_NOT_FOUND_MESSAGE

        svc = self._service()
        svc._run_nlm = MagicMock()

        with self.assertRaisesRegex(RuntimeError, ARTIFACT_NOT_FOUND_MESSAGE):
            svc.download('artifact-a', output_dir='/tmp', user_id='user-b')
        svc._run_nlm.assert_not_called()


class TestNotebookLmServiceStateConcurrency(unittest.TestCase):
    """다중 worker 상태 병합과 원자적 저장 회귀 테스트."""

    def test_stale_writer_only_merges_its_user_namespace(self):
        """오래된 worker가 다른 사용자와 로컬 상태를 덮어쓰지 않는다."""
        from services.notebooklm import notebooklm_service as service_module

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, 'notebooklm_state.json')
            with patch.object(service_module, 'STATE_FILE', state_path):
                local_worker = service_module.NotebookLmService()
                stale_user_worker = service_module.NotebookLmService()
                stale_same_user_worker = service_module.NotebookLmService()

                local_worker._save_state(None, {
                    'notebook_id': 'legacy-notebook',
                    'sources': {'legacy-url': 'legacy-source'},
                    'artifacts': {
                        'legacy-artifact': {'notebook_id': 'legacy-notebook'},
                    },
                })
                stale_user_worker._save_state('user-a', {
                    'notebook_id': 'user-a-notebook',
                    'sources': {'user-a-url': 'user-a-source'},
                    'artifacts': {
                        'user-a-artifact': {'notebook_id': 'user-a-notebook'},
                    },
                })
                stale_same_user = stale_same_user_worker._namespace_state(
                    'user-a',
                )
                stale_same_user['sources']['late-url'] = 'late-source'
                stale_same_user_worker._save_state('user-a')
                # user-a를 알지 못하는 이전 로컬 스냅샷을 다시 저장해도
                # users 레지스트리는 유지되어야 한다.
                local_worker._state['sources'][
                    'second-local-url'
                ] = 'second-local-source'
                local_worker._save_state()

                with open(state_path, 'r', encoding='utf-8') as state_file:
                    saved = json.load(state_file)

        self.assertEqual(saved['notebook_id'], 'legacy-notebook')
        self.assertEqual(saved['sources']['legacy-url'], 'legacy-source')
        self.assertEqual(
            saved['sources']['second-local-url'],
            'second-local-source',
        )
        self.assertIn('legacy-artifact', saved['artifacts'])
        self.assertIn('user-a-artifact', saved['users']['user-a']['artifacts'])
        self.assertEqual(
            saved['users']['user-a']['notebook_id'],
            'user-a-notebook',
        )
        self.assertEqual(
            saved['users']['user-a']['sources']['late-url'],
            'late-source',
        )

    def test_state_lock_is_exclusive_across_processes(self):
        """잠금 보유 중에는 다른 프로세스가 배타 잠금을 못 잡는다."""
        from services.notebooklm import notebooklm_service as service_module

        if service_module.fcntl is None:
            self.skipTest('fcntl을 지원하지 않는 플랫폼입니다.')

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, 'notebooklm_state.json')
            with patch.object(service_module, 'STATE_FILE', state_path):
                service = service_module.NotebookLmService()
                context = multiprocessing.get_context('spawn')
                result_queue = context.Queue()

                with service._state_lock():
                    contender = context.Process(
                        target=_probe_file_lock,
                        args=(f'{state_path}.lock', result_queue),
                    )
                    contender.start()
                    self.assertFalse(result_queue.get(timeout=20))
                    contender.join(timeout=20)

                self.assertEqual(contender.exitcode, 0)
                result_queue.close()

                # 잠금 해제 후에는 같은 probe가 성공해야 한다.
                unlocked_queue = context.Queue()
                unlocked_probe = context.Process(
                    target=_probe_file_lock,
                    args=(f'{state_path}.lock', unlocked_queue),
                )
                unlocked_probe.start()
                self.assertTrue(unlocked_queue.get(timeout=20))
                unlocked_probe.join(timeout=20)
                self.assertEqual(unlocked_probe.exitcode, 0)
                unlocked_queue.close()

    def test_notebook_operation_rechecks_state_after_waiting(self):
        """노트북 잠금 대기 후 최신 ID를 보고 CLI 중복 생성을 막는다."""
        from services.notebooklm import notebooklm_service as service_module

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, 'notebooklm_state.json')
            with patch.object(service_module, 'STATE_FILE', state_path):
                owner = service_module.NotebookLmService()
                waiter = service_module.NotebookLmService()
                attempted = threading.Event()
                results = []
                errors = []
                original_operation_lock = waiter._operation_lock

                @contextmanager
                def notifying_lock(operation, user_id, resource_key=''):
                    attempted.set()
                    with original_operation_lock(
                        operation,
                        user_id,
                        resource_key,
                    ):
                        yield

                waiter._operation_lock = notifying_lock
                waiter._run_nlm = MagicMock()

                def ensure_notebook():
                    try:
                        results.append(waiter._ensure_notebook('user-a'))
                    except Exception as exc:  # pragma: no cover - 실패 보고용
                        errors.append(exc)

                with owner._operation_lock('notebook', 'user-a'):
                    contender = threading.Thread(target=ensure_notebook)
                    contender.start()
                    self.assertTrue(attempted.wait(timeout=5))
                    owner._save_state('user-a', {
                        'notebook_id': 'existing-notebook',
                    })

                contender.join(timeout=5)

        self.assertFalse(contender.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(results, ['existing-notebook'])
        waiter._run_nlm.assert_not_called()

    def test_operation_lock_is_cross_process_and_resource_scoped(self):
        """같은 작업 키는 프로세스 간 직렬화되고 다른 키는 막지 않는다."""
        from services.notebooklm import notebooklm_service as service_module

        if service_module.fcntl is None:
            self.skipTest('fcntl을 지원하지 않는 플랫폼입니다.')

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, 'notebooklm_state.json')
            with patch.object(service_module, 'STATE_FILE', state_path):
                service = service_module.NotebookLmService()
                held_path = service._operation_lock_path(
                    'source',
                    'user-a',
                    'notebook-a\0url-a',
                )
                other_path = service._operation_lock_path(
                    'source',
                    'user-a',
                    'notebook-a\0url-b',
                )
                self.assertNotEqual(held_path, other_path)

                context = multiprocessing.get_context('spawn')
                held_queue = context.Queue()
                other_queue = context.Queue()
                with service._operation_lock(
                    'source',
                    'user-a',
                    'notebook-a\0url-a',
                ):
                    held_probe = context.Process(
                        target=_probe_file_lock,
                        args=(held_path, held_queue),
                    )
                    other_probe = context.Process(
                        target=_probe_file_lock,
                        args=(other_path, other_queue),
                    )
                    held_probe.start()
                    other_probe.start()
                    self.assertFalse(held_queue.get(timeout=20))
                    self.assertTrue(other_queue.get(timeout=20))
                    held_probe.join(timeout=20)
                    other_probe.join(timeout=20)

                self.assertEqual(held_probe.exitcode, 0)
                self.assertEqual(other_probe.exitcode, 0)
                held_queue.close()
                other_queue.close()

    def test_source_operation_rechecks_state_after_waiting(self):
        """소스 잠금 대기 후 최신 URL을 보고 CLI 중복 추가를 막는다."""
        from services.notebooklm import notebooklm_service as service_module

        notebook_id = 'existing-notebook'
        source_url = 'https://example.com/video'
        resource_key = f'{notebook_id}\0{source_url}'
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, 'notebooklm_state.json')
            with patch.object(service_module, 'STATE_FILE', state_path):
                owner = service_module.NotebookLmService()
                waiter = service_module.NotebookLmService()
                attempted = threading.Event()
                results = []
                errors = []
                original_operation_lock = waiter._operation_lock

                @contextmanager
                def notifying_lock(operation, user_id, key=''):
                    attempted.set()
                    with original_operation_lock(operation, user_id, key):
                        yield

                waiter._operation_lock = notifying_lock
                waiter._run_nlm = MagicMock()

                def add_source():
                    try:
                        results.append(waiter._add_source(
                            notebook_id,
                            source_url,
                            '자막',
                            'user-a',
                        ))
                    except Exception as exc:  # pragma: no cover - 실패 보고용
                        errors.append(exc)

                with owner._operation_lock(
                    'source',
                    'user-a',
                    resource_key,
                ):
                    contender = threading.Thread(target=add_source)
                    contender.start()
                    self.assertTrue(attempted.wait(timeout=5))
                    owner._save_state('user-a', {
                        'notebook_id': notebook_id,
                        'sources': {source_url: 'existing-source'},
                    })

                contender.join(timeout=5)

        self.assertFalse(contender.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(results, ['existing-source'])
        waiter._run_nlm.assert_not_called()

    def test_concurrent_processes_preserve_users_sources_and_artifacts(self):
        """같은 초기 스냅샷을 읽은 프로세스들의 추가 결과가 모두 남는다."""
        initial_state = {
            'notebook_id': 'legacy-notebook',
            'sources': {'legacy-url': 'legacy-source'},
            'artifacts': {
                'legacy-artifact': {'notebook_id': 'legacy-notebook'},
            },
            'users': {
                'existing-user': {
                    'notebook_id': 'existing-notebook',
                    'sources': {},
                    'artifacts': {},
                },
            },
        }
        writer_specs = [
            (
                None,
                'legacy-notebook',
                'local-url',
                'local-source',
                'local-artifact',
            ),
            (
                'user-a',
                'user-a-notebook',
                'user-a-url-1',
                'user-a-source-1',
                'user-a-artifact-1',
            ),
            (
                'user-a',
                'user-a-notebook',
                'user-a-url-2',
                'user-a-source-2',
                'user-a-artifact-2',
            ),
            (
                'user-b',
                'user-b-notebook',
                'user-b-url',
                'user-b-source',
                'user-b-artifact',
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, 'notebooklm_state.json')
            with open(state_path, 'w', encoding='utf-8') as state_file:
                json.dump(initial_state, state_file)

            context = multiprocessing.get_context('spawn')
            ready_queue = context.Queue()
            start_event = context.Event()
            processes = [
                context.Process(
                    target=_concurrent_state_writer,
                    args=(
                        state_path,
                        user_id,
                        notebook_id,
                        source_url,
                        source_id,
                        artifact_id,
                        ready_queue,
                        start_event,
                    ),
                )
                for (
                    user_id,
                    notebook_id,
                    source_url,
                    source_id,
                    artifact_id,
                ) in writer_specs
            ]

            try:
                for process in processes:
                    process.start()
                for _ in processes:
                    ready_queue.get(timeout=20)
                start_event.set()
                for process in processes:
                    process.join(timeout=20)
                self.assertEqual(
                    [process.exitcode for process in processes],
                    [0] * len(processes),
                )
            finally:
                start_event.set()
                for process in processes:
                    if process.is_alive():
                        process.terminate()
                    process.join(timeout=5)
                ready_queue.close()

            with open(state_path, 'r', encoding='utf-8') as state_file:
                saved = json.load(state_file)

        self.assertEqual(
            set(saved['sources']),
            {'legacy-url', 'local-url'},
        )
        self.assertEqual(
            set(saved['artifacts']),
            {'legacy-artifact', 'local-artifact'},
        )
        self.assertEqual(
            set(saved['users']),
            {'existing-user', 'user-a', 'user-b'},
        )
        self.assertEqual(
            set(saved['users']['user-a']['sources']),
            {'user-a-url-1', 'user-a-url-2'},
        )
        self.assertEqual(
            set(saved['users']['user-a']['artifacts']),
            {'user-a-artifact-1', 'user-a-artifact-2'},
        )
        self.assertIn('user-b-artifact', saved['users']['user-b']['artifacts'])

    def test_long_lived_worker_refreshes_artifact_ownership(self):
        """기존 worker가 다른 worker가 저장한 artifact를 재시작 없이 본다."""
        from services.notebooklm import notebooklm_service as service_module

        artifacts = [
            {'id': 'new-artifact', 'type': 'audio', 'status': 'completed'},
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, 'notebooklm_state.json')
            with patch.object(service_module, 'STATE_FILE', state_path):
                reader = service_module.NotebookLmService()
                writer = service_module.NotebookLmService()
                writer._save_state('user-a', {
                    'notebook_id': 'user-a-notebook',
                    'artifacts': {
                        'new-artifact': {
                            'notebook_id': 'user-a-notebook',
                            'source_id': 'source-a',
                            'content_type': 'audio',
                        },
                    },
                })
                reader._run_nlm = MagicMock(return_value=MagicMock(
                    returncode=0,
                    stdout=json.dumps(artifacts),
                    stderr='',
                ))

                result = reader.check_status('new-artifact', user_id='user-a')

        self.assertEqual(result, {'status': 'completed', 'type': 'audio'})
        reader._run_nlm.assert_called_once_with([
            'studio', 'status', 'user-a-notebook', '--json',
        ])

    def test_save_uses_fsync_and_atomic_replace(self):
        """상태를 fsync한 임시 파일로 쓴 뒤 os.replace로 교체한다."""
        from services.notebooklm import notebooklm_service as service_module

        original_fsync = os.fsync
        original_replace = os.replace
        write_events = []

        def recording_fsync(file_descriptor):
            file_mode = os.fstat(file_descriptor).st_mode
            target_type = (
                'file-fsync' if stat.S_ISREG(file_mode)
                else 'directory-fsync'
            )
            write_events.append(target_type)
            return original_fsync(file_descriptor)

        def recording_replace(source, destination):
            write_events.append('replace')
            return original_replace(source, destination)

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, 'notebooklm_state.json')
            with patch.object(service_module, 'STATE_FILE', state_path):
                with patch.object(
                    service_module.os,
                    'fsync',
                    side_effect=recording_fsync,
                ):
                    with patch.object(
                        service_module.os,
                        'replace',
                        side_effect=recording_replace,
                    ) as mock_replace:
                        service = service_module.NotebookLmService()
                        service._save_state(None, {
                            'notebook_id': 'legacy-notebook',
                            'sources': {},
                            'artifacts': {},
                        })

            self.assertEqual(write_events[:2], ['file-fsync', 'replace'])
            if len(write_events) == 3:
                self.assertEqual(write_events[2], 'directory-fsync')
            else:
                self.assertEqual(len(write_events), 2)
            mock_replace.assert_called_once()
            replace_source, replace_destination = mock_replace.call_args.args
            self.assertEqual(replace_destination, state_path)
            self.assertEqual(os.path.dirname(replace_source), temp_dir)
            self.assertFalse(os.path.exists(replace_source))
            self.assertEqual(
                [
                    name for name in os.listdir(temp_dir)
                    if name.endswith('.tmp')
                ],
                [],
            )

    def test_atomic_replace_failure_cleans_temp_and_keeps_previous_state(self):
        """os.replace 실패 시 임시 파일을 지우고 기존 상태를 유지한다."""
        from services.notebooklm import notebooklm_service as service_module

        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = os.path.join(temp_dir, 'notebooklm_state.json')
            with patch.object(service_module, 'STATE_FILE', state_path):
                service = service_module.NotebookLmService()
                service._save_state(None, {
                    'notebook_id': 'legacy-notebook',
                    'sources': {'existing-url': 'existing-source'},
                })
                with patch.object(
                    service_module.os,
                    'replace',
                    side_effect=OSError('교체 실패'),
                ):
                    with self.assertRaisesRegex(OSError, '교체 실패'):
                        service._save_state(None, {
                            'sources': {'new-url': 'new-source'},
                        })

                with open(state_path, 'r', encoding='utf-8') as state_file:
                    saved = json.load(state_file)
                temp_files = [
                    name for name in os.listdir(temp_dir)
                    if name.endswith('.tmp')
                ]

        self.assertEqual(
            saved['sources'],
            {'existing-url': 'existing-source'},
        )
        self.assertEqual(temp_files, [])


if __name__ == '__main__':
    unittest.main()
