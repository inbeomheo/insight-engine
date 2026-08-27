"""NotebookLM CLI(nlm) 래핑 서비스.

nlm CLI를 subprocess로 호출하여 노트북 관리, 소스 추가,
콘텐츠 생성, 상태 폴링, 다운로드를 수행한다.
"""
import copy
import hashlib
import json
import os
import re
import subprocess
import logging
import tempfile
import threading
import weakref
from contextlib import contextmanager, nullcontext
from typing import Callable, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows 이식성 폴백
    fcntl = None

try:
    import msvcrt
except ImportError:  # pragma: no cover - Unix 환경
    msvcrt = None

logger = logging.getLogger(__name__)

ARTIFACT_NOT_READY_MESSAGE = '아직 완료되지 않은 artifact입니다.'
ARTIFACT_NOT_FOUND_MESSAGE = 'artifact를 찾을 수 없습니다.'
STATE_FILE = os.path.join('data', 'notebooklm_state.json')

# flock은 프로세스 간 조정을, 경로별 RLock은 같은 프로세스의
# 스레드 간 조정을 담당한다. os.replace로 교체되는 상태 파일
# 대신 고정된 .lock 파일을 잠금 대상으로 사용한다.
_THREAD_LOCKS = weakref.WeakValueDictionary()
_THREAD_LOCKS_GUARD = threading.Lock()


def _thread_lock_for(lock_path: str) -> threading.RLock:
    """같은 파일 잠금을 사용하는 스레드들에 RLock을 공유한다."""
    with _THREAD_LOCKS_GUARD:
        thread_lock = _THREAD_LOCKS.get(lock_path)
        if thread_lock is None:
            thread_lock = threading.RLock()
            _THREAD_LOCKS[lock_path] = thread_lock
        return thread_lock


# nlm CLI 명령 타임아웃 (초)
CMD_TIMEOUT = 60
GENERATE_TIMEOUT = 120


class NotebookLmService:
    """NotebookLM CLI 래핑 서비스."""

    def __init__(self):
        # __new__로 만든 기존 단위 테스트 대역은 디스크와 동기화하지
        # 않도록 정상 초기화된 인스턴스만 파일 기반으로 표시한다.
        self._state_file_backed = True
        self._state = self._load_state()

    # ── 상태 저장/로드 ──

    @staticmethod
    def _normalize_state(state: object) -> dict:
        """상태 파일의 후방 호환 구조를 보장한다."""
        if not isinstance(state, dict):
            state = {}

        state.setdefault('notebook_id', None)
        if not isinstance(state.get('sources'), dict):
            state['sources'] = {}
        if not isinstance(state.get('artifacts'), dict):
            state['artifacts'] = {}
        if not isinstance(state.get('users'), dict):
            state['users'] = {}

        for user_key, namespace in list(state['users'].items()):
            if not isinstance(namespace, dict):
                namespace = {}
                state['users'][user_key] = namespace
            namespace.setdefault('notebook_id', None)
            if not isinstance(namespace.get('sources'), dict):
                namespace['sources'] = {}
            if not isinstance(namespace.get('artifacts'), dict):
                namespace['artifacts'] = {}
        return state

    @staticmethod
    def _state_path() -> str:
        return os.path.abspath(STATE_FILE)

    @contextmanager
    def _file_lock(self, lock_path: str):
        """지정한 파일에 스레드·프로세스 간 배타 잠금을 적용한다."""
        lock_path = os.path.abspath(lock_path)
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        thread_lock = _thread_lock_for(lock_path)

        with thread_lock:
            with open(lock_path, 'a+b') as lock_file:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                elif msvcrt is not None:  # pragma: no cover - Windows 전용
                    lock_file.seek(0)
                    if not lock_file.read(1):
                        lock_file.write(b'\0')
                        lock_file.flush()
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                else:  # pragma: no cover - 현대 CPython에서는 도달하지 않음
                    raise RuntimeError('이 플랫폼에서 파일 잠금을 사용할 수 없습니다.')
                try:
                    yield
                finally:
                    if fcntl is not None:
                        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    elif msvcrt is not None:  # pragma: no cover - Windows 전용
                        lock_file.seek(0)
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)

    @contextmanager
    def _state_lock(self):
        """스레드와 프로세스 간 배타적 상태 잠금을 획득한다."""
        with self._file_lock(f'{self._state_path()}.lock'):
            yield

    def _operation_lock_path(
        self,
        operation: str,
        user_id: Optional[str],
        resource_key: str = '',
    ) -> str:
        """사용자·리소스별 외부 생성 작업 잠금 경로를 만든다."""
        namespace_key = (
            'local' if user_id is None
            else f'user:{user_id}'
        )
        identity = '\0'.join((operation, namespace_key, resource_key))
        digest = hashlib.sha256(identity.encode('utf-8')).hexdigest()
        return f'{self._state_path()}.{operation}.{digest}.lock'

    @contextmanager
    def _operation_lock(
        self,
        operation: str,
        user_id: Optional[str],
        resource_key: str = '',
    ):
        """같은 사용자·리소스의 외부 CLI 생성 작업만 직렬화한다."""
        lock_path = self._operation_lock_path(
            operation,
            user_id,
            resource_key,
        )
        with self._file_lock(lock_path):
            yield

    def _read_state_unlocked(self) -> dict:
        try:
            with open(self._state_path(), 'r', encoding='utf-8') as f:
                state = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            state = {}
        return self._normalize_state(state)

    def _load_state(self) -> dict:
        with self._state_lock():
            return self._read_state_unlocked()

    def _refresh_state(self) -> dict:
        """디스크의 최신 상태를 다시 읽어 오래 살아 있는 worker를 갱신한다."""
        if not getattr(self, '_state_file_backed', False):
            return self._state
        # 읽기와 인메모리 교체를 같은 스레드 잠금 안에서 수행해
        # 느린 읽기가 방금 저장된 더 새로운 self._state를 되돌리지 않게 한다.
        with self._state_lock():
            self._state = self._read_state_unlocked()
            return self._state

    @staticmethod
    def _merge_namespace(target: dict, patch: dict) -> None:
        """해당 네임스페이스의 변경분만 병합한다."""
        for key, value in patch.items():
            if key in ('sources', 'artifacts') and isinstance(value, dict):
                current = target.setdefault(key, {})
                if not isinstance(current, dict):
                    current = {}
                    target[key] = current
                # 동일 URL/ID를 두 worker가 동시에 추가한 경우 먼저 저장된
                # 레코드를 권위 있는 결과로 유지한다.
                for item_key, item_value in value.items():
                    current.setdefault(item_key, copy.deepcopy(item_value))
            elif key == 'notebook_id':
                # 동시 최초 생성이 겹쳐도 먼저 저장된 노트북으로
                # 수렴한다. 오래된 None도 신규 ID를 지우지 못한다.
                if not target.get('notebook_id') and value:
                    target[key] = copy.deepcopy(value)
            else:
                target[key] = copy.deepcopy(value)

        target.setdefault('notebook_id', None)
        target.setdefault('sources', {})
        target.setdefault('artifacts', {})

    def _namespace_patch(self, user_id: Optional[str]) -> dict:
        """현재 메모리 상태에서 저장할 네임스페이스만 복사한다."""
        if user_id is None:
            return {
                key: copy.deepcopy(value)
                for key, value in self._state.items()
                if key != 'users'
            }

        namespace = self._state.get('users', {}).get(str(user_id), {})
        return copy.deepcopy(namespace) if isinstance(namespace, dict) else {}

    def _atomic_write_state(self, state: dict) -> None:
        """임시 파일을 동기화한 뒤 원자적으로 상태 파일을 교체한다."""
        state_path = self._state_path()
        state_dir = os.path.dirname(state_path)
        fd, temp_path = tempfile.mkstemp(
            dir=state_dir,
            prefix=f'.{os.path.basename(state_path)}.',
            suffix='.tmp',
        )
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as temp_file:
                json.dump(state, temp_file, ensure_ascii=False, default=str)
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temp_path, state_path)
            temp_path = ''

            # rename 메타데이터도 장애 직후 복구되도록 디렉토리를
            # 동기화한다. 일부 파일 시스템이 지원하지 않을 때만 건너뛴다.
            directory_flag = getattr(os, 'O_DIRECTORY', 0)
            try:
                directory_fd = os.open(state_dir, os.O_RDONLY | directory_flag)
            except OSError:
                directory_fd = None
            if directory_fd is not None:
                try:
                    os.fsync(directory_fd)
                except OSError:
                    logger.debug('NotebookLM 상태 디렉토리 fsync 미지원', exc_info=True)
                finally:
                    os.close(directory_fd)
        finally:
            if temp_path:
                try:
                    os.unlink(temp_path)
                except FileNotFoundError:
                    pass

    def _save_state(
        self,
        user_id: Optional[str] = None,
        namespace_patch: Optional[dict] = None,
    ) -> None:
        """최신 파일에 변경된 네임스페이스만 병합해 저장한다.

        ``namespace_patch``를 생략하면 기존 내부 호출 관습처럼
        현재 메모리의 해당 네임스페이스 전체를 병합한다.
        """
        patch = copy.deepcopy(
            namespace_patch if namespace_patch is not None
            else self._namespace_patch(user_id)
        )
        if not isinstance(patch, dict):
            raise TypeError('NotebookLM 상태 패치는 dict여야 합니다.')
        if user_id is None:
            # 로컬 네임스페이스는 최상위 users 레지스트리를 포함하지
            # 않는다. 호출자가 self._state 전체를 넘겨도 다른 사용자를
            # 덮어쓰지 못하게 한다.
            patch.pop('users', None)

        with self._state_lock():
            latest = self._read_state_unlocked()
            if user_id is None:
                self._merge_namespace(latest, patch)
            else:
                users = latest.setdefault('users', {})
                user_key = str(user_id)
                target = users.setdefault(
                    user_key,
                    {'notebook_id': None, 'sources': {}, 'artifacts': {}},
                )
                if not isinstance(target, dict):
                    target = {
                        'notebook_id': None,
                        'sources': {},
                        'artifacts': {},
                    }
                    users[user_key] = target
                self._merge_namespace(target, patch)

            latest = self._normalize_state(latest)
            self._atomic_write_state(latest)
            self._state = latest

    def _namespace_state(
        self,
        user_id: Optional[str],
        *,
        create: bool = True,
    ) -> Optional[dict]:
        """사용자별 NotebookLM 상태를 반환한다.

        Supabase가 비활성화된 로컬 개발 환경(user_id=None)은 기존 최상위
        상태를 재사용한다. 인증 사용자는 반드시 독립된 하위 네임스페이스를
        사용하여 노트북, 소스, artifact 소유권을 공유하지 않는다.
        """
        if user_id is None:
            return self._state

        users = self._state.setdefault('users', {})
        namespace = users.get(str(user_id))
        if namespace is None and create:
            namespace = {'notebook_id': None, 'sources': {}, 'artifacts': {}}
            users[str(user_id)] = namespace
        if namespace is not None:
            namespace.setdefault('notebook_id', None)
            namespace.setdefault('sources', {})
            namespace.setdefault('artifacts', {})
        return namespace

    def _owned_artifact(
        self,
        artifact_id: str,
        user_id: Optional[str],
    ) -> Optional[dict]:
        """인증 사용자가 생성한 artifact 메타데이터만 반환한다."""
        self._refresh_state()
        namespace = self._namespace_state(user_id, create=False)
        if namespace is None:
            return None
        artifact = namespace.get('artifacts', {}).get(artifact_id)
        if artifact is not None:
            return artifact

        # 소유권 레지스트리 도입 전 로컬 상태와만 호환한다. 인증된
        # 사용자에게는 미등록 artifact를 절대 허용하지 않는다.
        if user_id is None and namespace.get('notebook_id'):
            return {'notebook_id': namespace['notebook_id']}
        return None

    # ── CLI 실행 ──

    def _run_nlm(self, args: list[str], timeout: int = CMD_TIMEOUT) -> subprocess.CompletedProcess:
        env = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
        return subprocess.run(
            ['nlm'] + args,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            env=env,
        )

    # ── 인증 ──

    def check_auth(self) -> dict:
        """nlm login --check 결과를 반환한다."""
        try:
            result = self._run_nlm(['login', '--check'])
        except FileNotFoundError:
            return {'valid': False, 'message': 'nlm CLI가 설치되지 않았습니다. pip install notebooklm-mcp-cli 실행 후 nlm login을 해주세요.'}
        except subprocess.TimeoutExpired:
            return {'valid': False, 'message': '인증 확인 시간이 초과되었습니다.'}

        if result.returncode == 0:
            email = None
            for line in result.stdout.splitlines():
                if 'Account:' in line:
                    email = line.split('Account:')[-1].strip()
                    break
            return {'valid': True, 'email': email}
        else:
            return {'valid': False, 'message': '인증이 만료되었습니다. 터미널에서 nlm login을 실행해주세요.'}

    # ── 노트북 관리 ──

    def _ensure_notebook(
        self,
        user_id: Optional[str] = None,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> str:
        """노트북이 없으면 생성하고, 있으면 기존 ID 반환."""
        operation_lock = (
            self._operation_lock('notebook', user_id)
            if getattr(self, '_state_file_backed', False)
            else nullcontext()
        )
        with operation_lock:
            # 대기 중 다른 worker가 생성했을 수 있으므로 잠금을
            # 획득한 뒤 반드시 최신 상태를 다시 읽는다.
            self._refresh_state()
            namespace = self._namespace_state(user_id)
            if namespace.get('notebook_id'):
                return namespace['notebook_id']

            if on_cost_start is not None:
                on_cost_start()
            result = self._run_nlm(['notebook', 'create', 'Insight Engine'])
            if result.returncode != 0:
                raise RuntimeError(f'노트북 생성 실패: {result.stderr[:300]}')

            notebook_id = self._extract_id(result.stdout)
            namespace['notebook_id'] = notebook_id
            self._save_state(user_id, {'notebook_id': notebook_id})
            return self._namespace_state(user_id)['notebook_id']

    # ── 소스 관리 ──

    def _add_source(
        self,
        notebook_id: str,
        url: str,
        text: str,
        user_id: Optional[str] = None,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> str:
        """자막을 소스로 추가한다. URL 기준 중복 방지."""
        resource_key = f'{notebook_id}\0{url}'
        operation_lock = (
            self._operation_lock('source', user_id, resource_key)
            if getattr(self, '_state_file_backed', False)
            else nullcontext()
        )
        with operation_lock:
            # 동일 URL 작업이 먼저 끝났는지 잠금 획득 후 재확인한다.
            self._refresh_state()
            namespace = self._namespace_state(user_id)
            if url in namespace.get('sources', {}):
                return namespace['sources'][url]

            if on_cost_start is not None:
                on_cost_start()
            result = self._run_nlm([
                'source', 'add', notebook_id,
                '--text', text,
                '--title', url,
            ])
            if result.returncode != 0:
                raise RuntimeError(f'소스 추가 실패: {result.stderr[:300]}')

            source_id = self._extract_id(result.stdout)
            namespace.setdefault('sources', {})[url] = source_id
            self._save_state(user_id, {'sources': {url: source_id}})
            return self._namespace_state(user_id)['sources'][url]

    # ── 콘텐츠 생성 ──

    # nlm CLI 명령어 매핑
    CONTENT_COMMANDS = {
        'audio': ['audio', 'create'],
        'video': ['video', 'create'],
        'infographic': ['infographic', 'create'],
        'slide_deck': ['slides', 'create'],
        'mindmap': ['mindmap', 'create'],
        'quiz': ['quiz', 'create'],
        'flashcards': ['flashcards', 'create'],
        'briefing': ['report', 'create'],
        'study_guide': ['report', 'create'],
    }

    CONTENT_OPTIONS = {
        'audio': ['--format', 'deep_dive', '--language', 'ko'],
        'video': ['--format', 'explainer', '--style', 'classic', '--language', 'ko'],
        'infographic': ['--orientation', 'landscape', '--detail', 'detailed', '--style', 'professional', '--language', 'ko'],
        'slide_deck': ['--format', 'detailed_deck', '--language', 'ko'],
        'mindmap': ['--language', 'ko'],
        'quiz': ['--count', '10', '--difficulty', '3', '--language', 'ko'],
        'flashcards': ['--difficulty', 'medium', '--language', 'ko'],
        'briefing': ['--format', 'Briefing Doc', '--language', 'ko'],
        'study_guide': ['--format', 'Study Guide', '--language', 'ko'],
    }

    def generate(
        self,
        content_type: str,
        url: str,
        source_text: str,
        user_id: Optional[str] = None,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> dict:
        """콘텐츠 생성을 시작하고 artifact_id를 반환한다."""
        if content_type not in self.CONTENT_COMMANDS:
            raise ValueError(f'지원하지 않는 콘텐츠 타입: {content_type}')

        notebook_id = self._ensure_notebook(
            user_id,
            on_cost_start=on_cost_start,
        )
        source_id = self._add_source(
            notebook_id,
            url,
            source_text,
            user_id,
            on_cost_start=on_cost_start,
        )

        cmd = self.CONTENT_COMMANDS[content_type]
        options = self.CONTENT_OPTIONS.get(content_type, [])

        args = cmd + [notebook_id] + options + ['--confirm']
        if on_cost_start is not None:
            on_cost_start()
        result = self._run_nlm(args, timeout=GENERATE_TIMEOUT)

        if result.returncode != 0:
            raise RuntimeError(f'콘텐츠 생성 실패: {result.stderr[:300]}')

        artifact_id = self._extract_id(result.stdout)
        namespace = self._namespace_state(user_id)
        namespace.setdefault('artifacts', {})[artifact_id] = {
            'notebook_id': notebook_id,
            'source_id': source_id,
            'content_type': content_type,
        }
        artifact_meta = copy.deepcopy(namespace['artifacts'][artifact_id])
        self._save_state(user_id, {'artifacts': {artifact_id: artifact_meta}})
        return {
            'artifact_id': artifact_id,
            'notebook_id': notebook_id,
            'source_id': source_id,
            'content_type': content_type,
            'status': 'in_progress',
        }

    # ── 상태 폴링 ──

    def check_status(self, artifact_id: str, user_id: Optional[str] = None) -> dict:
        """artifact_id의 생성 상태를 확인한다."""
        artifact = self._owned_artifact(artifact_id, user_id)
        if artifact is None:
            return {'status': 'not_found', 'error': ARTIFACT_NOT_FOUND_MESSAGE}

        notebook_id = artifact.get('notebook_id')
        if not notebook_id:
            return {'status': 'not_found', 'error': ARTIFACT_NOT_FOUND_MESSAGE}

        result = self._run_nlm(['studio', 'status', notebook_id, '--json'])
        if result.returncode != 0:
            logger.error(
                'NotebookLM 상태 확인 실패 (artifact_id=%s): %s',
                artifact_id,
                result.stderr[:300],
            )
            return {'status': 'failed', 'error': 'NotebookLM 상태를 확인하지 못했습니다.'}

        try:
            # nlm이 JSON 앞에 ANSI 코드를 넣을 수 있으므로 첫 [ 또는 { 부터 파싱
            stdout = result.stdout
            json_start = min(
                (stdout.find('['), stdout.find('{')),
                key=lambda x: x if x >= 0 else float('inf')
            )
            if json_start < 0 or json_start == float('inf'):
                return {'status': 'failed', 'error': '상태 파싱 실패'}

            artifacts = json.loads(stdout[json_start:])
        except (json.JSONDecodeError, ValueError):
            return {'status': 'failed', 'error': '상태 응답 파싱 실패'}

        for artifact in artifacts:
            if artifact.get('id') == artifact_id:
                return {
                    'status': artifact.get('status', 'unknown'),
                    'type': artifact.get('type'),
                }

        return {'status': 'not_found', 'error': f'artifact {artifact_id}를 찾을 수 없습니다.'}

    # ── 다운로드 ──

    DOWNLOAD_COMMANDS = {
        'audio': 'audio',
        'video': 'video',
        'report': 'report',
        'briefing': 'report',
        'study_guide': 'report',
        'slide_deck': 'slide-deck',
        'slide-deck': 'slide-deck',
        'mindmap': 'mind-map',
        'mind_map': 'mind-map',
        'mind-map': 'mind-map',
        'infographic': 'infographic',
        'quiz': 'quiz',
        'flashcards': 'flashcards',
    }

    def download(
        self,
        artifact_id: str,
        output_dir: str = None,
        user_id: Optional[str] = None,
    ) -> str:
        """artifact를 파일로 다운로드하고 경로를 반환한다."""
        import tempfile
        artifact = self._owned_artifact(artifact_id, user_id)
        if artifact is None or not artifact.get('notebook_id'):
            raise RuntimeError(ARTIFACT_NOT_FOUND_MESSAGE)
        notebook_id = artifact['notebook_id']

        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix='nlm_')

        # artifact 타입 확인
        status = self.check_status(artifact_id, user_id=user_id)
        if status.get('status') == 'not_found':
            raise RuntimeError(ARTIFACT_NOT_FOUND_MESSAGE)
        if status.get('status') != 'completed':
            raise RuntimeError(f'{ARTIFACT_NOT_READY_MESSAGE} 상태: {status.get("status")}')

        # 생성 시 저장한 content_type이 CLI 상태 표현보다 안정적이다.
        # 기존 로컬 artifact만 상태 응답의 type을 폴백으로 사용한다.
        artifact_type = artifact.get('content_type') or status.get('type') or 'report'
        download_type = self.DOWNLOAD_COMMANDS.get(artifact_type)
        if download_type is None:
            raise RuntimeError(f'지원하지 않는 artifact 타입입니다: {artifact_type}')

        ext_map = {
            'audio': '.mp3',
            'video': '.mp4',
            'slide_deck': '.pdf',
            'slide-deck': '.pdf',
            'infographic': '.png',
            'mindmap': '.json',
            'mind_map': '.json',
            'mind-map': '.json',
            'quiz': '.html',
            'flashcards': '.md',
            'briefing': '.md',
            'study_guide': '.md',
        }
        ext = ext_map.get(artifact_type, '.md')
        output_path = os.path.join(output_dir, f'{artifact_id}{ext}')

        args = ['download', download_type, notebook_id, artifact_id]
        if artifact_type == 'quiz':
            args += ['--format', 'html']
        elif artifact_type == 'flashcards':
            args += ['--format', 'markdown']
        args += ['--output', output_path]

        result = self._run_nlm(args, timeout=GENERATE_TIMEOUT)

        if result.returncode != 0:
            raise RuntimeError(f'다운로드 실패: {result.stderr[:300]}')

        return output_path

    # ── YouTube 자막 추출 (폴백용) ──

    def extract_youtube_transcript(
        self,
        video_url: str,
        on_cost_start: Optional[Callable[[], None]] = None,
    ) -> Optional[str]:
        """YouTube URL에서 NotebookLM을 통해 자막을 추출한다.

        자막 추출 폴백으로 사용. 노트북이 없으면 None 반환.
        """
        self._refresh_state()
        notebook_id = self._state.get('notebook_id')
        if not notebook_id:
            return None

        # 상태 확인과 노트북 미설정 폴백은 무비용이다. 실제
        # NotebookLM에 YouTube 소스를 할당하는 첫 CLI 호출 직전에
        # 사용량을 확정한다. 콜백은 try 밖에 두어 임대 상실
        # 등의 예외이 기존 graceful fallback에 삼켜지지 않게 한다.
        if on_cost_start is not None:
            on_cost_start()

        try:
            # YouTube 소스 추가 (--wait로 처리 완료까지 대기)
            self._run_nlm([
                'source', 'add', notebook_id,
                '--youtube', video_url, '--wait',
            ])

            # 소스 목록에서 가장 최근 youtube 타입 찾기
            list_result = self._run_nlm(['source', 'list', notebook_id, '--json'])
            if list_result.returncode != 0:
                return None

            sources = json.loads(list_result.stdout)
            youtube_source = None
            for src in reversed(sources):
                if src.get('type') == 'youtube':
                    youtube_source = src
                    break

            if not youtube_source:
                return None

            # 소스 내용 가져오기
            get_result = self._run_nlm(['source', 'get', youtube_source['id'], '--json'])
            if get_result.returncode != 0:
                return None

            data = json.loads(get_result.stdout)
            content = data.get('value', {}).get('content', '')
            return content if content and content.strip() else None

        except (subprocess.TimeoutExpired, json.JSONDecodeError, RuntimeError):
            return None
        except Exception:
            return None

    # ── 유틸 ──

    def _extract_id(self, output: str) -> str:
        """nlm CLI 출력에서 ID를 추출한다."""
        # "ID: <uuid>" 패턴
        match = re.search(r'ID:\s*([a-f0-9-]{36})', output)
        if match:
            return match.group(1)
        # "Source ID: <uuid>" 패턴
        match = re.search(r'Source ID:\s*([a-f0-9-]{36})', output)
        if match:
            return match.group(1)
        # "Artifact ID: <uuid>" 패턴
        match = re.search(r'Artifact ID:\s*([a-f0-9-]{36})', output)
        if match:
            return match.group(1)
        raise RuntimeError(f'출력에서 ID를 추출할 수 없습니다: {output[:200]}')
