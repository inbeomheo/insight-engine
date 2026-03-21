"""NotebookLM CLI(nlm) 래핑 서비스.

nlm CLI를 subprocess로 호출하여 노트북 관리, 소스 추가,
콘텐츠 생성, 상태 폴링, 다운로드를 수행한다.
"""
import json
import os
import re
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)

STATE_FILE = os.path.join('data', 'notebooklm_state.json')

# nlm CLI 명령 타임아웃 (초)
CMD_TIMEOUT = 60
GENERATE_TIMEOUT = 120


class NotebookLmService:
    """NotebookLM CLI 래핑 서비스."""

    def __init__(self):
        self._state = self._load_state()

    # ── 상태 저장/로드 ──

    def _load_state(self) -> dict:
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {'notebook_id': None, 'sources': {}}

    def _save_state(self):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(self._state, f, ensure_ascii=False, default=str)

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

    def _ensure_notebook(self) -> str:
        """노트북이 없으면 생성하고, 있으면 기존 ID 반환."""
        if self._state.get('notebook_id'):
            return self._state['notebook_id']

        result = self._run_nlm(['notebook', 'create', 'Insight Engine'])
        if result.returncode != 0:
            raise RuntimeError(f'노트북 생성 실패: {result.stderr[:300]}')

        notebook_id = self._extract_id(result.stdout)
        self._state['notebook_id'] = notebook_id
        self._save_state()
        return notebook_id

    # ── 소스 관리 ──

    def _add_source(self, notebook_id: str, url: str, text: str) -> str:
        """자막을 소스로 추가한다. URL 기준 중복 방지."""
        if url in self._state.get('sources', {}):
            return self._state['sources'][url]

        result = self._run_nlm([
            'source', 'add', notebook_id,
            '--text', text,
            '--title', url,
        ])
        if result.returncode != 0:
            raise RuntimeError(f'소스 추가 실패: {result.stderr[:300]}')

        source_id = self._extract_id(result.stdout)
        self._state.setdefault('sources', {})[url] = source_id
        self._save_state()
        return source_id

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

    def generate(self, content_type: str, url: str, source_text: str) -> dict:
        """콘텐츠 생성을 시작하고 artifact_id를 반환한다."""
        if content_type not in self.CONTENT_COMMANDS:
            raise ValueError(f'지원하지 않는 콘텐츠 타입: {content_type}')

        notebook_id = self._ensure_notebook()
        source_id = self._add_source(notebook_id, url, source_text)

        cmd = self.CONTENT_COMMANDS[content_type]
        options = self.CONTENT_OPTIONS.get(content_type, [])

        args = cmd + [notebook_id] + options + ['--confirm']
        result = self._run_nlm(args, timeout=GENERATE_TIMEOUT)

        if result.returncode != 0:
            raise RuntimeError(f'콘텐츠 생성 실패: {result.stderr[:300]}')

        artifact_id = self._extract_id(result.stdout)
        return {
            'artifact_id': artifact_id,
            'notebook_id': notebook_id,
            'source_id': source_id,
            'content_type': content_type,
            'status': 'in_progress',
        }

    # ── 상태 폴링 ──

    def check_status(self, artifact_id: str) -> dict:
        """artifact_id의 생성 상태를 확인한다."""
        notebook_id = self._state.get('notebook_id')
        if not notebook_id:
            return {'status': 'failed', 'error': '노트북이 없습니다.'}

        result = self._run_nlm(['studio', 'status', notebook_id, '--json'])
        if result.returncode != 0:
            return {'status': 'failed', 'error': result.stderr[:300]}

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
        'slide_deck': 'slide-deck',
        'quiz': 'quiz',
    }

    def download(self, artifact_id: str, output_dir: str = None) -> str:
        """artifact를 파일로 다운로드하고 경로를 반환한다."""
        import tempfile
        notebook_id = self._state.get('notebook_id')
        if not notebook_id:
            raise RuntimeError('노트북이 없습니다.')

        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix='nlm_')

        # artifact 타입 확인
        status = self.check_status(artifact_id)
        if status.get('status') != 'completed':
            raise RuntimeError(f'아직 완료되지 않은 artifact입니다. 상태: {status.get("status")}')

        artifact_type = status.get('type', 'report')
        download_type = self.DOWNLOAD_COMMANDS.get(artifact_type, 'report')

        ext_map = {'audio': '.mp3', 'video': '.mp4', 'slide_deck': '.pdf', 'slide-deck': '.pdf'}
        ext = ext_map.get(artifact_type, '.md')
        output_path = os.path.join(output_dir, f'{artifact_id}{ext}')

        result = self._run_nlm([
            'download', download_type, notebook_id,
            '--output', output_path,
        ], timeout=GENERATE_TIMEOUT)

        if result.returncode != 0:
            raise RuntimeError(f'다운로드 실패: {result.stderr[:300]}')

        return output_path

    # ── YouTube 자막 추출 (폴백용) ──

    def extract_youtube_transcript(self, video_url: str) -> Optional[str]:
        """YouTube URL에서 NotebookLM을 통해 자막을 추출한다.

        자막 추출 폴백으로 사용. 노트북이 없으면 None 반환.
        """
        notebook_id = self._state.get('notebook_id')
        if not notebook_id:
            return None

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
