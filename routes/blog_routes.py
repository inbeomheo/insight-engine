"""
블로그 콘텐츠 생성 API 라우트

핵심 생성 엔드포인트만 포함:
- /generate (단일 URL 생성)
- /generate-batch (배치 처리)
- /api/generate-merged (통합 생성)
- /generate-stream (SSE 스트리밍)

유틸리티, 고급 생성, 내보내기, 통합 서비스 라우트는 별도 모듈:
- routes/utility_routes.py
- routes/advanced_routes.py
- routes/export_routes.py
- routes/integration_routes.py
"""
import concurrent.futures
import html as html_lib
import json
import threading
import time
import uuid
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app, g, Response, stream_with_context
from extensions import limiter
from utils.responses import (
    api_error,
    handle_error,
    sanitize_error_for_client,
    api_error_from_exception,
    safe_error_or_fallback,
)

from config import get_model_max_tokens
from services.core import ai_service, content_service
from src.contexts.identity.interface.auth_decorators import require_auth
from src.contexts.identity.domain.exceptions import QuotaExceeded
from src.shared.infrastructure.supabase_client import is_supabase_enabled, get_supabase
from src.contexts.content_library import save_history_entry as save_history
from services.usage import UsageAccountingUnavailable, require_usage
from services.usage.usage_decorator import (
    UsageChargeState,
    _ensure_usage_lease_valid,
    _release_usage_lease,
    capture_usage_charge_callback,
    get_usage_for_response,
    mark_usage_charge_committed,
)
from services.usage.usage_lock import (
    UsageLockBusy,
    UsageLockUnavailable,
    acquire_usage_request_lock,
)

blog_bp = Blueprint('blog', __name__)

DEFAULT_MODEL = 'cliproxyapi/gpt-5.5'
DEFAULT_STYLE = 'summary'
MAX_BATCH_URLS = 10
MAX_BATCH_WORKERS = 5
BATCH_CONTENT_TOKEN_LIMIT = 3000
DOCUMENT_MAGIC_BYTES = {
    '.pdf': b'%PDF',
    '.docx': b'PK\x03\x04',
    '.pptx': b'PK\x03\x04',
}
AUDIO_UPLOAD_EXTENSIONS = ('.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac')
MAX_MERGED_URLS = 5
VIDEO_QA_MAX_URL_CHARS = 2048
VIDEO_QA_MAX_QUESTION_CHARS = 500
VIDEO_QA_MAX_HISTORY_MESSAGES = 10
VIDEO_QA_MAX_HISTORY_USER_CHARS = 500
VIDEO_QA_MAX_HISTORY_ASSISTANT_CHARS = 2000
VIDEO_QA_MAX_HISTORY_TOTAL_CHARS = 10000

# 에러 응답 헬퍼 (기존 호출 호환)
_handle_error_response = handle_error
_sanitize_error_for_client = sanitize_error_for_client


def _format_byte_limit(size_bytes: int) -> str:
    """Return a compact Korean byte limit label for upload errors."""
    mb = 1024 * 1024
    kb = 1024
    if size_bytes >= mb:
        value = size_bytes / mb
        return f"{int(value) if value.is_integer() else round(value, 1)}MB"
    if size_bytes >= kb:
        value = size_bytes / kb
        return f"{int(value) if value.is_integer() else round(value, 1)}KB"
    return f"{size_bytes}바이트"


def _normalize_extracted_text(text: str) -> str:
    """Normalize extracted document text while preserving paragraph breaks."""
    import re

    normalized = re.sub(r"\r\n?", "\n", text or "")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _validate_video_qa_history(history):
    """Validate and normalize bounded follow-up conversation history."""
    if history is None:
        return [], None
    if not isinstance(history, list):
        return None, 'history는 배열 형식이어야 합니다.'
    if len(history) > VIDEO_QA_MAX_HISTORY_MESSAGES:
        return None, f'history는 최대 {VIDEO_QA_MAX_HISTORY_MESSAGES}개까지 허용됩니다.'

    normalized = []
    total_chars = 0
    for item in history:
        if not isinstance(item, dict):
            return None, 'history 항목 형식이 올바르지 않습니다.'
        role = item.get('role')
        content = item.get('content')
        if role not in {'user', 'assistant'} or not isinstance(content, str):
            return None, 'history의 role/content 형식이 올바르지 않습니다.'
        content = content.strip()
        if not content:
            return None, 'history 메시지는 비어 있을 수 없습니다.'
        max_chars = (
            VIDEO_QA_MAX_HISTORY_USER_CHARS
            if role == 'user'
            else VIDEO_QA_MAX_HISTORY_ASSISTANT_CHARS
        )
        if len(content) > max_chars:
            return None, f'history의 {role} 메시지는 {max_chars}자 이내여야 합니다.'
        total_chars += len(content)
        if total_chars > VIDEO_QA_MAX_HISTORY_TOTAL_CHARS:
            return None, f'history 전체는 {VIDEO_QA_MAX_HISTORY_TOTAL_CHARS}자 이내여야 합니다.'
        normalized.append({'role': role, 'content': content})

    return normalized, None


def _get_document_extension(uploaded_file) -> str:
    filename = (uploaded_file.filename or "").lower()
    for extension in DOCUMENT_MAGIC_BYTES:
        if filename.endswith(extension):
            return extension
    return ""


def _is_supported_document_upload(uploaded_file, file_bytes: bytes) -> bool:
    """Validate extension and magic bytes for supported document uploads."""
    extension = _get_document_extension(uploaded_file)
    return bool(extension and file_bytes.startswith(DOCUMENT_MAGIC_BYTES[extension]))


def _get_audio_extension(uploaded_file) -> str:
    filename = (uploaded_file.filename or "").lower()
    for extension in AUDIO_UPLOAD_EXTENSIONS:
        if filename.endswith(extension):
            return extension
    return ""


def _has_mp3_sync(file_bytes: bytes) -> bool:
    return len(file_bytes) >= 2 and file_bytes[0] == 0xFF and (file_bytes[1] & 0xE0) == 0xE0


def _is_supported_audio_upload(uploaded_file, file_bytes: bytes) -> bool:
    """Best-effort audio signature validation; Whisper remains the decode backstop."""
    extension = _get_audio_extension(uploaded_file)
    if not extension:
        return False

    if extension == '.wav':
        return file_bytes.startswith(b'RIFF') and file_bytes[8:12] == b'WAVE'
    if extension == '.mp3':
        return file_bytes.startswith(b'ID3') or _has_mp3_sync(file_bytes)
    if extension == '.m4a':
        return b'ftyp' in file_bytes[:16]
    if extension == '.ogg':
        return file_bytes.startswith(b'OggS')
    if extension == '.flac':
        return file_bytes.startswith(b'fLaC')

    # Raw AAC can be ADTS/ADIF/LOAS, so keep validation to extension allow-list
    # and rely on Whisper failure/empty transcript handling for final rejection.
    if extension == '.aac':
        return True

    return False


def _document_read_error_message(message: str) -> str:
    for label in ('PDF', 'DOCX', 'PPTX'):
        if message.startswith(f'{label} 파일을 읽을 수 없습니다'):
            return f'{label} 파일을 읽을 수 없습니다. 파일이 손상되었을 수 있습니다.'
    return message


def _get_upload_size(uploaded_file) -> int | None:
    """Return FileStorage payload size without consuming the stream."""
    stream = getattr(uploaded_file, "stream", None)
    if stream is None:
        return getattr(uploaded_file, "content_length", None) or None

    try:
        pos = stream.tell()
        stream.seek(0, 2)
        size = stream.tell()
        stream.seek(pos)
        return size
    except (AttributeError, OSError):
        return getattr(uploaded_file, "content_length", None) or None


def _read_upload_magic(uploaded_file, length: int = 16) -> bytes:
    """Read upload magic bytes and rewind so downstream consumers can save the full file."""
    stream = uploaded_file.stream
    try:
        stream.seek(0)
        magic = stream.read(length)
        stream.seek(0)
        return magic
    except (AttributeError, OSError):
        return b""


def _validate_style(style, custom_prompt=None):
    """요청 스타일을 정규화합니다.

    내장 스타일은 공백을 제거한 STYLE_PROMPTS ID로 정규화하고,
    커스텀 스타일 등 알 수 없는 ID는 기존처럼 그대로 통과시킵니다.
    """
    if not isinstance(style, str):
        return DEFAULT_STYLE

    style_id = style.strip()
    if not style_id:
        return DEFAULT_STYLE

    from prompts import STYLE_PROMPTS
    if style_id in STYLE_PROMPTS:
        return style_id

    return style


def _extract_client_id(req) -> str:
    """요청에서 클라이언트 ID를 추출합니다."""
    data = req.get_json(silent=True)
    if isinstance(data, dict) and data.get('clientId'):
        return str(data['clientId'])

    form_id = req.form.get('clientId')
    if form_id:
        return str(form_id)

    raw = (req.get_data(cache=False, as_text=True) or '').strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed.get('clientId'):
                return str(parsed['clientId'])
        except json.JSONDecodeError:
            pass  # 잘못된 JSON은 무시하고 빈 문자열 반환

    return ''


def _get_request_data(req):
    """JSON 또는 form 데이터에서 공통 파라미터를 추출하고 검증합니다.
    API 키는 서버 환경변수에서 관리되므로 요청에서 추출하지 않습니다.
    """
    data = req.get_json(silent=True)
    if isinstance(data, dict) and data:
        from services.core.ai_service import resolve_public_model

        try:
            model = resolve_public_model(
                data.get('model'), DEFAULT_MODEL, allow_auto=True
            )
            model_error = None
        except ValueError as exc:
            model = DEFAULT_MODEL
            model_error = str(exc)
        # modifiers 검증
        modifiers, _ = _validate_modifiers(data.get('modifiers'))
        # custom_prompt 검증
        custom_prompt, _ = _validate_custom_prompt(data.get('customPrompt'))
        style = _validate_style(data.get('style', DEFAULT_STYLE), custom_prompt)

        # urls 검증 (리스트 형식 확인)
        urls = data.get('urls', [])
        if not isinstance(urls, list):
            urls = []
        urls = [u for u in urls if isinstance(u, str)][:MAX_BATCH_URLS]

        # source_type 검증
        _allowed_source_types = {
            'youtube', 'webpage', 'article', 'rss', 'arxiv', 'twitter',
            'reddit', 'github', 'hackernews', 'podcast',
        }
        raw_source_type = data.get('source_type')
        source_type = raw_source_type if raw_source_type in _allowed_source_types else None

        # detail_level 검증 (허용값: brief, standard, deep)
        _allowed_detail_levels = {'brief', 'standard', 'deep'}
        raw_detail = data.get('detail_level')
        detail_level = raw_detail if isinstance(raw_detail, str) and raw_detail in _allowed_detail_levels else 'standard'

        # output_format 검증 (허용값: html, markdown, plain)
        _allowed_formats = {'html', 'markdown', 'plain'}
        raw_format = data.get('output_format')
        output_format = raw_format if isinstance(raw_format, str) and raw_format in _allowed_formats else 'html'

        # max_chars 검증 (정수, 100~50000)
        raw_max_chars = data.get('max_chars')
        max_chars = None
        if raw_max_chars is not None:
            try:
                max_chars = int(raw_max_chars)
                if max_chars < 100 or max_chars > 50000:
                    max_chars = None
            except (ValueError, TypeError):
                max_chars = None

        # include_transcript 검증
        include_transcript = bool(data.get('include_transcript', False))

        # enable_citations 검증 (인용 타임스탬프 모드)
        enable_citations = bool(data.get('enable_citations', False))

        # transcript_language 검증 (자막 추출 언어 지정 — None이면 기존 기본 동작)
        transcript_language, transcript_language_error = _validate_transcript_language(data.get('transcript_language'))

        return {
            'url': data.get('url') if isinstance(data.get('url'), str) else None,
            'urls': urls,
            'content': data.get('content') if isinstance(data.get('content'), str) else None,
            'model': model,
            'model_error': model_error,
            'style': style,
            'modifiers': modifiers,
            'custom_prompt': custom_prompt,
            'analyze': bool(data.get('analyze', False)),
            'source_type': source_type,
            'detail_level': detail_level,
            'output_format': output_format,
            'max_chars': max_chars,
            'include_transcript': include_transcript,
            'enable_citations': enable_citations,
            'transcript_language': transcript_language,
            'transcript_language_error': transcript_language_error,
        }

    # form 데이터에서 modifiers JSON 파싱 (파일 업로드 시 FormData로 전송)
    form_modifiers = None
    raw_modifiers = req.form.get('modifiers')
    if raw_modifiers:
        try:
            parsed = json.loads(raw_modifiers)
            if isinstance(parsed, dict):
                form_modifiers, _ = _validate_modifiers(parsed)
        except (json.JSONDecodeError, ValueError):
            pass

    custom_prompt, _ = _validate_custom_prompt(req.form.get('customPrompt'))
    style = _validate_style(req.form.get('style', DEFAULT_STYLE), custom_prompt)
    transcript_language, transcript_language_error = _validate_transcript_language(req.form.get('transcript_language'))

    from services.core.ai_service import resolve_public_model
    try:
        model = resolve_public_model(
            req.form.get('model'), DEFAULT_MODEL, allow_auto=True
        )
        model_error = None
    except ValueError as exc:
        model = DEFAULT_MODEL
        model_error = str(exc)

    return {
        'url': req.form.get('url'),
        'urls': [],
        'content': req.form.get('content'),
        'model': model,
        'model_error': model_error,
        'style': style,
        'modifiers': form_modifiers,
        'custom_prompt': custom_prompt,
        'analyze': False,
        'source_type': None,
        'detail_level': req.form.get('detail_level', 'standard'),
        'output_format': req.form.get('output_format', 'html'),
        'max_chars': None,
        'include_transcript': False,
        'enable_citations': False,
        'transcript_language': transcript_language,
        'transcript_language_error': transcript_language_error,
    }


def _validate_modifiers(modifiers):
    """modifiers 파라미터의 유효성을 검증합니다.

    Args:
        modifiers: dict 또는 None

    Returns:
        tuple: (validated_modifiers, error_message)
    """
    if modifiers is None:
        return None, None

    if not isinstance(modifiers, dict):
        return None, 'modifiers는 객체 형식이어야 합니다.'

    # 허용된 키와 값 정의 (v3.1: 3개 모디파이어 지원)
    allowed_keys = {'length', 'writing_style', 'language'}
    allowed_values = {
        'length': {'short', 'medium', 'long'},
        'writing_style': {'conversational', 'explanatory', 'casual', 'expert'},
        'language': {'ko', 'en', 'ja'},
    }

    validated = {}
    for key, value in modifiers.items():
        if key not in allowed_keys:
            continue  # 알 수 없는 키는 무시
        if not isinstance(value, str):
            continue
        # 값 검증
        if key in allowed_values and value not in allowed_values[key]:
            continue  # 잘못된 값은 무시
        validated[key] = value[:50]  # 길이 제한

    return validated, None


_ALLOWED_TRANSCRIPT_LANGUAGES = {'ko', 'en', 'ja'}


def _validate_transcript_language(transcript_language):
    """transcript_language 파라미터의 유효성을 검증합니다.

    Args:
        transcript_language: None 또는 언어 코드 문자열('ko'/'en'/'ja')

    Returns:
        tuple: (validated_language, error_message)
        - validated_language: None(자동/미지정) 또는 검증된 언어 코드
        - error_message: 유효하지 않은 값이면 한국어 에러 메시지, 아니면 None
    """
    if transcript_language is None or transcript_language == '':
        return None, None

    if not isinstance(transcript_language, str) or transcript_language not in _ALLOWED_TRANSCRIPT_LANGUAGES:
        return None, '지원하지 않는 자막 언어입니다. (ko, en, ja 중 선택)'

    return transcript_language, None


def _validate_custom_prompt(custom_prompt):
    """customPrompt 파라미터의 유효성을 검증합니다.

    Returns:
        tuple: (validated_prompt, error_message)
    """
    if custom_prompt is None:
        return None, None

    if not isinstance(custom_prompt, str):
        return None, 'customPrompt는 문자열이어야 합니다.'

    # 길이 제한 (2000자)
    return custom_prompt.strip()[:2000], None


# ── 생성 헬퍼 (분리된 모듈에서 import) ──────────────────────────
from routes.generation_helpers import (
    _fetch_youtube_content,
    _handle_short_content_bypass, _handle_cache_hit,
    _call_ai_with_comments, _save_and_respond, _persist_generation_result,
    _process_single_url,
    _get_style_prompt, _handle_direct_text,
    _handle_web_source,
    _get_style_label, _apply_output_format,
    _generate_comment_summary, _combine_results,
    _validate_direct_text_content,
)


# ── 핵심 생성 엔드포인트 ──────────────────────────────────────


@blog_bp.route('/api/extract-document', methods=['POST'])
@limiter.limit("15/minute")
@require_auth
def extract_document():
    """문서 파일에서 텍스트를 추출해 직접 텍스트 입력 경로에 재사용합니다."""
    from config import (
        DIRECT_TEXT_MAX_CHARS,
        DIRECT_TEXT_MIN_CHARS,
        DOCUMENT_UPLOAD_MAX_BYTES,
        DOCUMENT_UPLOAD_REQUEST_OVERHEAD_BYTES,
    )
    from services.content.document_ingest_service import extract_from_upload

    if (
        request.content_length
        and request.content_length > DOCUMENT_UPLOAD_MAX_BYTES + DOCUMENT_UPLOAD_REQUEST_OVERHEAD_BYTES
    ):
        return api_error(
            f'문서 파일 크기는 최대 {_format_byte_limit(DOCUMENT_UPLOAD_MAX_BYTES)}까지 업로드할 수 있습니다.',
            400,
        )

    uploaded_file = request.files.get('file')
    if not uploaded_file or not uploaded_file.filename:
        return api_error('문서 파일을 업로드해 주세요.', 400)

    try:
        upload_size = _get_upload_size(uploaded_file)
        if upload_size is not None and upload_size > DOCUMENT_UPLOAD_MAX_BYTES:
            return api_error(
                f'문서 파일 크기는 최대 {_format_byte_limit(DOCUMENT_UPLOAD_MAX_BYTES)}까지 업로드할 수 있습니다.',
                400,
            )

        magic = _read_upload_magic(uploaded_file)
        if not magic or not _is_supported_document_upload(uploaded_file, magic):
            return api_error('PDF, DOCX, PPTX 파일만 업로드할 수 있습니다.', 400)

        try:
            doc = extract_from_upload(uploaded_file)
        except ValueError as exc:
            return api_error(_document_read_error_message(str(exc)), 400)

        text = _normalize_extracted_text(doc.get('content', ''))
        pages = int(doc.get('page_count') or 0)

        if len(text) < DIRECT_TEXT_MIN_CHARS:
            return api_error(
                '문서에서 충분한 텍스트를 추출하지 못했습니다 (스캔 이미지 문서는 지원하지 않습니다)',
                400,
            )

        truncated = len(text) > DIRECT_TEXT_MAX_CHARS
        if truncated:
            text = text[:DIRECT_TEXT_MAX_CHARS]

        return jsonify({
            'text': text,
            'truncated': truncated,
            'pages': pages,
        })
    except Exception as exc:
        current_app.logger.error('Unexpected document extraction error: %s', exc, exc_info=True)
        return api_error('문서 처리 중 오류가 발생했습니다. 다시 시도해 주세요.', 500)


@blog_bp.route('/api/extract-audio', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
def extract_audio():
    """오디오 파일을 Whisper로 전사해 직접 텍스트 입력 경로에 재사용합니다."""
    import importlib.util
    import os
    import tempfile
    from config import (
        AUDIO_UPLOAD_MAX_BYTES,
        DIRECT_TEXT_MAX_CHARS,
        DOCUMENT_UPLOAD_REQUEST_OVERHEAD_BYTES,
    )

    if os.getenv('WHISPER_ENABLED', 'false').lower() != 'true':
        return api_error('음성 전사를 위해 서버에 WHISPER_ENABLED=true 설정이 필요합니다.', 400)

    if importlib.util.find_spec('faster_whisper') is None:
        return api_error('음성 인식 모듈이 서버에 설치되어 있지 않습니다. 관리자에게 문의해 주세요.', 500)

    if (
        request.content_length
        and request.content_length > AUDIO_UPLOAD_MAX_BYTES + DOCUMENT_UPLOAD_REQUEST_OVERHEAD_BYTES
    ):
        return api_error(
            f'오디오 파일 크기는 최대 {_format_byte_limit(AUDIO_UPLOAD_MAX_BYTES)}까지 업로드할 수 있습니다.',
            400,
        )

    uploaded_file = request.files.get('file')
    if not uploaded_file or not uploaded_file.filename:
        return api_error('오디오 파일을 업로드해 주세요.', 400)

    audio_path = None
    whisper_service = None
    try:
        upload_size = _get_upload_size(uploaded_file)
        if upload_size is not None and upload_size > AUDIO_UPLOAD_MAX_BYTES:
            return api_error(
                f'오디오 파일 크기는 최대 {_format_byte_limit(AUDIO_UPLOAD_MAX_BYTES)}까지 업로드할 수 있습니다.',
                400,
            )

        magic = _read_upload_magic(uploaded_file)
        if not magic or not _is_supported_audio_upload(uploaded_file, magic):
            return api_error('MP3, WAV, M4A, OGG, FLAC, AAC 파일만 업로드할 수 있습니다.', 400)

        from services.transcript import whisper_service as _whisper_service
        whisper_service = _whisper_service

        suffix = _get_audio_extension(uploaded_file)
        fd, audio_path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        uploaded_file.save(audio_path)

        whisper_model = os.getenv('WHISPER_MODEL_SIZE', 'base')
        transcript_text = whisper_service.transcribe_audio(audio_path, whisper_model)
        text = _normalize_extracted_text(transcript_text or '')
        if not text:
            return api_error('음성 인식 결과가 비어 있습니다. 오디오 파일을 확인해주세요.', 400)

        truncated = len(text) > DIRECT_TEXT_MAX_CHARS
        if truncated:
            text = text[:DIRECT_TEXT_MAX_CHARS]

        return jsonify({
            'text': text,
            'truncated': truncated,
        })
    except Exception as exc:
        current_app.logger.error('Unexpected audio extraction error: %s', exc, exc_info=True)
        return api_error('오디오 처리 중 오류가 발생했습니다. 다시 시도해 주세요.', 500)
    finally:
        if audio_path and whisper_service:
            whisper_service._cleanup_file(audio_path)


@blog_bp.route('/generate', methods=['POST'])
@limiter.limit("15/minute")
@require_auth
@require_usage
def generate():
    """단일 URL에서 콘텐츠를 생성합니다 (YouTube, 웹페이지, RSS, arXiv 지원).
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용 (관리자는 무제한).
    """
    from services.content.multi_source_collector import detect_source_type, SOURCE_YOUTUBE

    try:
        start_time = time.time()
        params = _get_request_data(request)
        on_cost_start = capture_usage_charge_callback()

        if params.get('model_error'):
            return api_error(params['model_error'], 400, 'UNSUPPORTED_MODEL')

        # transcript_language 유효성 검증 (지원하지 않는 값이면 400)
        if params.get('transcript_language_error'):
            return api_error(params['transcript_language_error'], 400)

        url = params['url']
        direct_content = params.get('content')

        if url and direct_content is not None and direct_content.strip():
            return api_error('URL과 텍스트는 동시에 입력할 수 없습니다.', 400)

        # ── 직접 텍스트 입력 모드 ──
        if not url and direct_content is not None:
            validation_error = _validate_direct_text_content(direct_content)
            if validation_error:
                return api_error(validation_error, 400)
            if params['model'] == 'auto':
                params['model'] = ai_service.resolve_public_model(
                    params['model'], DEFAULT_MODEL, allow_auto=False
                )
            return _handle_direct_text(
                params,
                start_time,
                on_cost_start=on_cost_start,
            )

        if not url:
            return api_error('URL이 필요합니다.', 400)

        # ── 비YouTube 소스 (웹페이지 / RSS / arXiv) ──
        detected_source_type = detect_source_type(url)
        # 클라이언트 힌트로 수집기를 강제하면 임의 URL을 podcast/yt-dlp 경로로
        # 보낼 수 있다. 네트워크 대상은 서버가 URL에서 감지한 타입만 사용한다.
        source_type = detected_source_type
        if source_type != SOURCE_YOUTUBE:
            try:
                if params['model'] == 'auto':
                    params['model'] = ai_service.resolve_public_model(
                        params['model'], DEFAULT_MODEL, allow_auto=False
                    )
                return _handle_web_source(
                    params,
                    url,
                    source_type,
                    start_time,
                    on_cost_start=on_cost_start,
                )
            except ValueError as e:
                safe_message = safe_error_or_fallback(
                    str(e),
                    '[생성 실패] 콘텐츠를 가져올 수 없습니다.',
                )
                return api_error(safe_message, 400)

        # ── YouTube 흐름 ──
        if not content_service.is_youtube_url(url):
            return api_error('유효한 YouTube URL을 입력해주세요.', 400)

        video_id = content_service.get_video_id(url)
        if not video_id:
            return api_error('유효하지 않은 YouTube URL입니다.', 400)

        # 캐시 체크 — 자막/제목 추출 전에 선조회 (히트 시 YouTube I/O 전부 생략)
        from services.core.cache_service import AICacheService
        from services.core.ai_prompt_context import get_prompt_context_cache_scope
        request_data_all = request.get_json(silent=True) or {}
        force = bool(request_data_all.get('force', False))
        # These modes add dynamic or post-generation data that the compact
        # cache payload intentionally does not persist.  Recompute rather than
        # returning a semantically incomplete cached response.
        cache_bypass = force or any((
            bool(getattr(g, 'user_id', None)),
            bool(request_data_all.get('web_search', False)),
            bool(request_data_all.get('agent_mode', False)),
            bool(params.get('analyze', False)),
            bool(request_data_all.get('quality_check', False)),
        ))
        modifiers = params['modifiers'] or {}
        cache_style_prompt = _get_style_prompt(params['style'], params.get('custom_prompt'))
        cache_key = AICacheService.make_key(
            video_id, params['style'], params['model'],
            modifiers.get('length', 'medium'),
            modifiers.get('writing_style', 'conversational'),
            transcript_language=params.get('transcript_language'),
            enable_citations=params.get('enable_citations', False),
            context_scope=get_prompt_context_cache_scope(getattr(g, 'user_id', None)),
            style_prompt=cache_style_prompt,
            modifiers=modifiers,
            detail_level=params.get('detail_level', 'standard'),
            web_search=bool(request_data_all.get('web_search', False)),
            agent_mode=bool(request_data_all.get('agent_mode', False)),
            analyze=bool(params.get('analyze', False)),
            output_format=params.get('output_format', 'html'),
            max_chars=params.get('max_chars'),
        )
        cache_resp = _handle_cache_hit(
            cache_key, cache_bypass, video_id, url, start_time,
            transcript_language=params.get('transcript_language'),
            on_cost_start=on_cost_start,
        )
        if cache_resp:
            return cache_resp

        # 제목 조회와 자막/댓글 추출을 병렬 실행 (700-1500ms 절감)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            title_future = executor.submit(
                content_service.get_content_title,
                url,
                on_cost_start=on_cost_start,
            )
            content_future = executor.submit(
                _fetch_youtube_content,
                video_id,
                params.get('transcript_language'),
                on_cost_start,
            )
            youtube_title = title_future.result() or 'YouTube 영상'
            transcript_text, comments, error, raw_transcript, transcript_source, transcript_segments = content_future.result()
        if error:
            return api_error(error, 400)

        max_tokens = get_model_max_tokens(params['model'])
        main_content = f"[영상 자막]\n{transcript_text}"
        truncated_content = content_service.truncate_text(main_content, max_tokens)

        # 짧은 콘텐츠 바이패스
        bypass_resp = _handle_short_content_bypass(
            transcript_text, params['style'], youtube_title,
            raw_transcript, transcript_source, start_time
        )
        if bypass_resp:
            return bypass_resp

        # 에이전트 모드 여부 확인
        request_data_all = request.get_json(silent=True) or {}
        agent_mode = bool(request_data_all.get('agent_mode', False))

        # 챕터 분할 LLM 호출을 메인 생성과 병렬로 시작
        # (입력이 자막뿐이라 독립적 — 기존엔 메인 생성 후 직렬 호출로 응답 지연)
        chapter_future = None
        if transcript_segments:
            from routes.generation_helpers import _run_chapter_split
            _chapter_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            chapter_future = _chapter_executor.submit(
                _run_chapter_split, current_app._get_current_object(),
                raw_transcript,
                ai_service.resolve_public_model(
                    params['model'], DEFAULT_MODEL, allow_auto=False
                ),
                transcript_segments,
                on_cost_start,
            )
            _chapter_executor.shutdown(wait=False)

        style_prompt = _get_style_prompt(params['style'], params['custom_prompt'])
        agent_meta = None

        if agent_mode:
            # 멀티에이전트 파이프라인 실행
            try:
                from services.agents import Orchestrator
                user_id = getattr(g, 'user_id', None)
                orchestrator = Orchestrator(
                    model=ai_service.resolve_public_model(
                        params['model'], DEFAULT_MODEL, allow_auto=False
                    ),
                    on_cost_start=on_cost_start,
                )
                agent_output = orchestrator.run(
                    transcript=transcript_text,
                    style=params['style'],
                    style_prompt=style_prompt,
                    url=url,
                    modifiers=params['modifiers'] or {},
                    user_id=user_id,
                    detail_level=params.get('detail_level'),
                    web_search=bool(request_data_all.get('web_search', False)),
                )
                result = {
                    'title': agent_output['title'],
                    'content': agent_output['content'],
                    'html': agent_output['html'],
                    'usage': agent_output['usage'],
                }
                used_prompt = f'[에이전트 모드] {params["style"]}'
                comment_result = None
                agent_meta = {
                    'agent_mode': True,
                    'quality': agent_output.get('quality'),
                    'seo': agent_output.get('seo'),
                    'elapsed_time': agent_output.get('elapsed_time', 0),
                }
            except UsageLockUnavailable:
                raise
            except Exception as ae:
                current_app.logger.error(f'에이전트 모드 실패, 일반 모드로 폴백: {ae}')
                web_search = bool(request_data_all.get('web_search', False))
                result, used_prompt, comment_result = _call_ai_with_comments(
                    truncated_content, params['model'], style_prompt, params,
                    comments, transcript_text, max_tokens, web_search=web_search,
                    on_cost_start=on_cost_start,
                )
        else:
            web_search = bool(request_data_all.get('web_search', False))
            result, used_prompt, comment_result = _call_ai_with_comments(
                truncated_content, params['model'], style_prompt, params,
                comments, transcript_text, max_tokens, web_search=web_search,
                on_cost_start=on_cost_start,
            )

        # 인용 타임스탬프 처리 (enable_citations: true 요청 시)
        if params.get('enable_citations') and video_id:
            try:
                from services.content.citation_service import (
                    parse_citations, validate_citations,
                    enrich_content_with_links, enrich_html_with_links,
                    build_source_receipts,
                )
                # 인용 목록 파싱 + 검증은 링크 변환 전 원문 기준으로 수행
                citations = parse_citations(result.get('content', ''))
                citations = validate_citations(citations, transcript_segments or [])
                result['citations'] = citations
                result['source_receipts'] = build_source_receipts(
                    citations,
                    video_id,
                    datetime.now(timezone.utc).isoformat(),
                    source_title=youtube_title,
                )
                # 마크다운 내 [MM:SS] 링크 변환
                result['content'] = enrich_content_with_links(
                    result.get('content', ''), video_id
                )
                # HTML 내 [MM:SS] 링크 변환
                if result.get('html'):
                    result['html'] = enrich_html_with_links(
                        result['html'], video_id
                    )
            except Exception as cite_err:
                current_app.logger.warning(f"인용 처리 실패 (무시): {cite_err}")

        # 품질 평가 (quality_check: true 요청 시만)
        quality_score = None
        request_data = request_data_all
        if request_data.get('quality_check'):
            try:
                from services.quality.quality_service import evaluate_quality
                quality_score = evaluate_quality(
                    content=result.get('content', ''),
                    source_summary=transcript_text[:500],
                    on_cost_start=on_cost_start,
                )
                current_app.logger.info(
                    f"품질 평가 완료: grade={quality_score.get('grade')}, "
                    f"overall={quality_score.get('overall')}"
                )
            except UsageLockUnavailable:
                raise
            except Exception as qe:
                current_app.logger.warning(f"품질 평가 실패 (무시): {qe}")

        # 캐시 저장 + 히스토리 + 응답
        return _save_and_respond(
            result, used_prompt, comment_result, cache_key,
            video_id, params, url, youtube_title,
            raw_transcript, transcript_source, comments, start_time,
            quality_score=quality_score,
            agent_meta=agent_meta,
            transcript_segments=transcript_segments,
            chapter_future=chapter_future,
        )

    except UsageLockUnavailable:
        # 자막 유료 폴백 직전 임대 소유권을 잃은 경우
        # @require_usage의 표준 503 처리와 환불 경로로 전파한다.
        raise
    except UsageAccountingUnavailable as e:
        current_app.logger.error('Generate usage accounting unavailable: %s', e)
        return api_error(
            '사용량 기록 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.',
            503,
            'USAGE_ACCOUNTING_UNAVAILABLE',
        )
    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Generate failed: {e}")
        return _handle_error_response(str(e))


@blog_bp.route('/generate-batch', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
def generate_batch():
    """여러 URL을 배치로 처리합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용 (배치 전체가 1회로 계산, 관리자는 무제한).
    """
    from services.usage.usage_service import (
        InvalidIdempotencyReplay,
        InvalidIdempotencyKey,
        MAX_USAGE_COUNT,
        UsageReservationReplay,
        UsageService,
    )

    usage_lease = None
    usage_reservation = None
    reservation_settled = False
    usage_charge_state = UsageChargeState()
    try:
        current_app.logger.info("Batch generate request received")

        data = request.get_json()

        if not data or not isinstance(data, dict):
            current_app.logger.error("No JSON data received")
            return api_error('JSON 데이터가 제공되지 않았습니다', 400)

        urls = data.get('urls', [])
        try:
            model = ai_service.resolve_public_model(
                data.get('model'), DEFAULT_MODEL, allow_auto=False
            )
        except ValueError as exc:
            return api_error(str(exc), 400, 'UNSUPPORTED_MODEL')
        modifiers, _ = _validate_modifiers(data.get('modifiers'))
        custom_prompt, _ = _validate_custom_prompt(data.get('customPrompt'))
        style = _validate_style(data.get('style', DEFAULT_STYLE), custom_prompt)
        transcript_language, language_error = _validate_transcript_language(data.get('transcript_language'))
        if language_error:
            return api_error(language_error, 400)
        raw_detail = data.get('detail_level')
        detail_level = raw_detail if isinstance(raw_detail, str) and raw_detail in {'brief', 'standard', 'deep'} else 'standard'
        web_search = bool(data.get('web_search', data.get('enable_web_search', False)))
        agent_mode = bool(data.get('agent_mode', data.get('enable_agent_mode', False)))

        current_app.logger.info(
            "Batch request accepted: url_count=%d model=%s",
            len(urls) if isinstance(urls, list) else 0,
            model,
        )

        if not urls or not isinstance(urls, list):
            return api_error('URL 목록이 제공되지 않았습니다', 400)
        if len(urls) > MAX_BATCH_URLS:
            return api_error(f'최대 {MAX_BATCH_URLS}개의 URL만 처리할 수 있습니다', 400)
        if any(not isinstance(url, str) or not url.strip() for url in urls):
            return api_error('URL 목록에는 비어 있지 않은 주소 문자열만 입력해주세요.', 400)
        urls = [url.strip() for url in urls]

        # 입력 검증 뒤, 비용 작업 제출 전 원자적·멱등 예약을 확보한다.
        user_id = getattr(g, 'user_id', None)
        if is_supabase_enabled() and user_id:
            usage_lease = acquire_usage_request_lock(user_id)
            _ensure_usage_lease_valid(usage_lease)
        usage_reservation = UsageService.reserve_for_request(user_id)
        g.usage_reservation = usage_reservation
        g.usage_charge_state = usage_charge_state
        g.usage = usage_reservation.usage_before
        g.updated_usage = usage_reservation.usage_after
        _ensure_usage_lease_valid(usage_lease)

        app = current_app._get_current_object()
        results = [None] * len(urls)
        combined_content = []

        current_app.logger.info(f"Starting to process {len(urls)} URLs concurrently")

        # 임대가 유효하고 사용량 예약이 완료된 뒤에만 비용 작업을 시작한다.
        _ensure_usage_lease_valid(usage_lease)

        def _commit_batch_charge():
            # 자막 수집 중 임대를 잃었다면 AI 공급자에 들어가기 직전에
            # 중단한다. 상태 확정은 모든 worker가 공유하는 단방향 이벤트다.
            _ensure_usage_lease_valid(usage_lease)
            mark_usage_charge_committed(usage_charge_state)

        def _process_reserved_url(url):
            # 큐에 대기하던 worker도 실제 시작 순간에 임대를 다시
            # 확인해 소유권 상실 후 새 비용 작업에 진입하지 않는다.
            _ensure_usage_lease_valid(usage_lease)
            return _process_single_url(
                app, url, model, style, modifiers, custom_prompt,
                _commit_batch_charge,
                detail_level=detail_level, transcript_language=transcript_language,
                web_search=web_search, agent_mode=agent_mode, user_id=user_id,
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_BATCH_WORKERS) as executor:
            future_to_index = {
                executor.submit(_process_reserved_url, url): i
                for i, url in enumerate(urls)
            }

            try:
                for future in concurrent.futures.as_completed(future_to_index, timeout=600):
                    index = future_to_index[future]
                    try:
                        result = future.result(timeout=300)
                        results[index] = result
                        current_app.logger.info(f"Completed processing URL {index + 1}: {result.get('success', False)}")

                        if result['success'] and isinstance(result.get('content', ''), str):
                            combined_content.append(result['content'])
                    except UsageLockUnavailable:
                        raise
                    except concurrent.futures.TimeoutError:
                        current_app.logger.error(f"Timeout for URL {index + 1}")
                        results[index] = {
                            'success': False,
                            'url': urls[index],
                            'title': '시간 초과',
                            'error': '[타임아웃] 처리 시간이 초과되었습니다.'
                        }
                    except Exception as e:
                        current_app.logger.error(f"Exception in future for URL {index + 1}: {e}")
                        results[index] = {
                            'success': False,
                            'url': urls[index],
                            'title': '오류 발생',
                            'error': _sanitize_error_for_client(str(e))
                        }
            except concurrent.futures.TimeoutError:
                current_app.logger.error("Batch overall timeout (600s)")
                for future, index in future_to_index.items():
                    if results[index] is None:
                        future.cancel()
                        results[index] = {
                            'success': False,
                            'url': urls[index],
                            'title': '시간 초과',
                            'error': '[타임아웃] 배치 전체 처리 시간이 초과되었습니다.'
                        }

        url_to_result = {result['url']: result for result in results if result}
        ordered_results = [
            url_to_result.get(url, {'success': False, 'url': url, 'error': '처리 실패'})
            for url in urls
        ]

        final_combined_content = "\n\n=== 다음 콘텐츠 ===\n\n".join(combined_content) if combined_content else ""
        success_count = sum(1 for r in ordered_results if r.get('success'))
        fail_count = len(ordered_results) - success_count

        current_app.logger.info(f"Batch processing completed. Success: {success_count}, Failed: {fail_count}")

        updated_usage = usage_reservation.usage_after

        # P2 버그 #7 수정: 배치 히스토리 저장 (N+1 → 배치 INSERT)
        if g.user_id:
            histories_to_save = []
            for result in ordered_results:
                if result.get('success'):
                    report_id = str(uuid.uuid4())
                    result['id'] = report_id
                    histories_to_save.append({
                        'id': report_id,
                        'url': result.get('url'),
                        'title': result.get('title'),
                        'style': style,
                        'content': result.get('content', ''),
                        'html': result.get('html', ''),
                        'transcript': result.get('transcript'),
                        'transcript_source': result.get('transcript_source'),
                        'usage': result.get('usage'),
                        'elapsed_time': result.get('elapsed_time'),
                    })

            # 배치 INSERT — Content/Library BC에 위임 (sanitize + batch INSERT 통합 처리)
            if histories_to_save:
                from src.contexts.content_library import save_many_history_entries
                save_many_history_entries(g.user_id, histories_to_save)

        if success_count == 0 and not usage_charge_state.committed:
            # 어느 worker도 공급자에 들어가지 않은 전부 실패만 환불한다.
            updated_usage = UsageService.refund_reservation(
                user_id,
                usage_reservation,
            )
        reservation_settled = True

        return jsonify({
            'success': True,
            'results': ordered_results,
            'content': final_combined_content,
            'total_processed': len(urls),
            'successful': success_count,
            'failed': fail_count,
            'usage': updated_usage
        })

    except InvalidIdempotencyKey as e:
        return api_error(str(e), 400, 'INVALID_IDEMPOTENCY_KEY')
    except (InvalidIdempotencyReplay, UsageReservationReplay) as e:
        response = {
            'error': str(e),
            'code': 'IDEMPOTENCY_REPLAY',
        }
        if isinstance(e, UsageReservationReplay):
            response['usage'] = e.usage
        return jsonify(response), 409
    except QuotaExceeded:
        return jsonify({
            'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
            'code': 'USAGE_LIMIT_EXCEEDED',
            'usage': {
                'usage_count': 0,
                'max_usage': MAX_USAGE_COUNT,
                'can_use': False,
            },
        }), 429
    except UsageLockBusy:
        return api_error(
            '이 계정의 콘텐츠 생성 요청이 이미 진행 중입니다.',
            409,
            'USAGE_REQUEST_IN_PROGRESS',
        )
    except UsageLockUnavailable as e:
        current_app.logger.error('Batch usage lock unavailable: %s', e)
        return api_error(
            '사용량 확인 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.',
            503,
            'USAGE_LOCK_UNAVAILABLE',
        )
    except UsageAccountingUnavailable as e:
        current_app.logger.error('Batch usage accounting unavailable: %s', e)
        return api_error(
            '사용량 기록 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.',
            503,
            'USAGE_ACCOUNTING_UNAVAILABLE',
        )
    except ValueError as e:
        current_app.logger.error(f"ValueError in batch generate: {e}")
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Batch generate failed: {e}", exc_info=True)
        return api_error_from_exception(e, '배치 처리 중 오류가 발생했습니다.')
    finally:
        if (
            usage_reservation is not None
            and not reservation_settled
            and not usage_charge_state.committed
        ):
            UsageService.refund_reservation_quietly(
                getattr(g, 'user_id', None),
                usage_reservation,
            )
        if usage_lease is not None:
            _release_usage_lease(usage_lease)


@blog_bp.route('/api/generate-merged', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def generate_merged():
    """여러 YouTube URL의 자막을 합쳐 하나의 통합 콘텐츠를 생성합니다.
    2~5개 URL 지원, AI 호출 1회, 사용량 1회 차감.
    """
    try:
        start_time = time.time()
        params = _get_request_data(request)
        on_cost_start = capture_usage_charge_callback()
        if params.get('model_error'):
            return api_error(params['model_error'], 400, 'UNSUPPORTED_MODEL')
        params['model'] = ai_service.resolve_public_model(
            params['model'], DEFAULT_MODEL, allow_auto=False
        )
        if params.get('transcript_language_error'):
            return api_error(params['transcript_language_error'], 400)

        urls = params['urls']

        if len(urls) < 2:
            return api_error('합쳐서 생성은 최소 2개 URL이 필요합니다.', 400)
        if len(urls) > MAX_MERGED_URLS:
            return api_error(f'최대 {MAX_MERGED_URLS}개 URL까지 합칠 수 있습니다.', 400)

        # URL 유효성 검사
        for url in urls:
            if not content_service.is_youtube_url(url):
                return api_error(f'유효하지 않은 YouTube URL: {url}', 400)

        # 병렬로 자막+댓글 추출
        app = current_app._get_current_object()
        transcript_language = params.get('transcript_language')
        video_data = []  # (url, video_id, title, transcript, comments, source)

        def _fetch_one(url):
            with app.app_context():
                try:
                    vid = content_service.get_video_id(url)
                    if not vid:
                        return {'url': url, 'error': '유효하지 않은 YouTube URL'}
                    title = content_service.get_content_title(
                        url,
                        on_cost_start=on_cost_start,
                    ) or 'YouTube 영상'
                    transcript_text, comments, error, _, source, _ = _fetch_youtube_content(
                        vid,
                        transcript_language,
                        on_cost_start,
                    )
                    if error:
                        return {'url': url, 'error': error, 'title': title}
                    return {
                        'url': url, 'video_id': vid, 'title': title,
                        'transcript': transcript_text, 'comments': comments,
                        'transcript_source': source,
                    }
                except UsageLockUnavailable:
                    raise
                except Exception as e:
                    current_app.logger.error('Merged fetch failed for %s: %s', url, e, exc_info=True)
                    return {
                        'url': url,
                        'title': '알 수 없는 영상',
                        'error': _sanitize_error_for_client(str(e))
                    }

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_MERGED_URLS, len(urls))) as executor:
            futures = {executor.submit(_fetch_one, u): u for u in urls}
            for future in concurrent.futures.as_completed(futures):
                video_data.append(future.result())

        # URL 순서 복원
        url_order = {u: i for i, u in enumerate(urls)}
        video_data.sort(key=lambda d: url_order.get(d['url'], 99))

        # 실패 URL 확인
        successes = [d for d in video_data if 'transcript' in d]
        if len(successes) < 2:
            errors = [f"{d['title']}: {d['error']}" for d in video_data if 'error' in d]
            return jsonify({
                'error': f'자막 추출 성공이 2개 미만입니다. 실패: {"; ".join(errors)}'
            }), 400

        # 토큰 예산 분배 후 합성
        max_tokens = get_model_max_tokens(params['model'])
        prompt_overhead = 4000
        available_tokens = max_tokens - prompt_overhead
        per_url_tokens = available_tokens // len(successes)

        merged_parts = []
        all_comments = []
        source_videos = []

        for d in successes:
            truncated = content_service.truncate_text(d['transcript'], per_url_tokens)
            merged_parts.append(f"[영상 {len(merged_parts) + 1}: {d['title']}]\n{truncated}")
            if d['comments']:
                all_comments.extend(d['comments'][:10])
            source_videos.append({
                'url': d['url'],
                'title': d['title'],
                'transcript_source': d['transcript_source'],
            })

        merged_content = '\n\n'.join(merged_parts)
        if all_comments:
            comments_text = '\n'.join(all_comments[:30])
            merged_content += f"\n\n[시청자 댓글 (종합)]\n{comments_text}"

        # AI 호출 1회
        style_prompt = _get_style_prompt(params['style'], params['custom_prompt'])
        result, used_prompt = ai_service.create_content(
            merged_content, params['model'], style_prompt,
            return_prompt=True, modifiers=params['modifiers'],
            style_id=params['style'],
            detail_level=params.get('detail_level'),
            on_cost_start=on_cost_start,
        )

        elapsed_time = round(time.time() - start_time, 2)
        report_id = str(uuid.uuid4())

        # 히스토리 저장 (첫 번째 URL 기준)
        if g.user_id:
            save_history(g.user_id, {
                'id': report_id,
                'url': urls[0],
                'title': result.get('title', '통합 분석'),
                'style': params['style'],
                'content': result.get('content', ''),
                'html': result.get('html', ''),
                'transcript': None,
                'usage': result.get('usage'),
                'elapsed_time': elapsed_time,
            })

        # SEO 메타데이터
        seo = None
        if params['style'] == 'blog_seo':
            seo = ai_service.extract_seo_metadata(result.get('content', ''))

        # GEO 메타데이터
        geo = None
        if params['style'] == 'geo_seo':
            geo = ai_service.extract_geo_metadata(result.get('content', ''))

        return jsonify({
            **result,
            'id': report_id,
            'elapsed_time': elapsed_time,
            'source_videos': source_videos,
            'merged': True,
            'seo': seo,
            'geo': geo,
            'quota': get_usage_for_response(),
        })

    except UsageLockUnavailable:
        raise
    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Generate merged failed: {e}")
        return _handle_error_response(str(e))


@blog_bp.route('/generate-stream', methods=['POST'])
@limiter.limit("15/minute")
@require_auth
def generate_stream():
    """SSE 스트리밍으로 콘텐츠를 생성합니다.
    @require_usage 데코레이터 사용 불가 (generator 응답) → 수동 사용량 관리.
    """
    from services.usage.usage_service import (
        InvalidIdempotencyReplay,
        InvalidIdempotencyKey,
        MAX_USAGE_COUNT,
        UsageReservationReplay,
        UsageService,
    )
    import markdown as md_lib

    usage_lease = None
    usage_lease_owned_by_response = False
    usage_enabled = False
    account_usage = None
    usage_reservation = None
    user_id = None
    stream_state = {
        'settled': False,
        'charge_committed': False,
    }
    stream_state_guard = threading.Lock()

    def _commit_stream_charge() -> bool:
        """Finalize the existing DB reservation immediately before AI cost starts.

        A client disconnect may race with generator progress. If the close path
        already refunded the reservation, return False so no provider work starts
        after that refund. Once cost starts, later disconnects/errors must not turn
        the consumed provider work into a quota refund.
        """
        with stream_state_guard:
            if stream_state['settled']:
                return stream_state['charge_committed']
            stream_state['settled'] = True
            stream_state['charge_committed'] = True
            return True

    def _start_stream_cost() -> None:
        """자막·AI 공급자 진입 직전의 단일 fail-closed 경계."""
        _ensure_usage_lease_valid(usage_lease)
        if not _commit_stream_charge():
            raise UsageLockUnavailable(
                '이미 종료된 스트림 예약으로 비용 작업을 시작할 수 없습니다.'
            )

    def _refund_stream_reservation(*, quiet: bool) -> dict | None:
        """스트림 종료 경로에서 예약을 최대 한 번 논리적으로 환불한다.

        종료 훅과 generator finally가 모두 호출될 수 있으므로 DB RPC 자체도
        멱등이지만, 프로세스 내 중복 호출도 잠금으로 줄인다.
        """
        nonlocal account_usage
        if usage_reservation is None:
            return account_usage
        with stream_state_guard:
            if stream_state['settled']:
                return account_usage
            try:
                account_usage = UsageService.refund_reservation(
                    user_id,
                    usage_reservation,
                )
            except UsageAccountingUnavailable:
                if quiet:
                    # generator 오류를 가리지는 않되, settled로 표시하지 않아
                    # response close 훅에서 같은 멱등 RPC를 다시 시도할 수 있게 한다.
                    return account_usage
                raise
            stream_state['settled'] = True
            stream_state['charge_committed'] = False
            return account_usage

    try:
        start_time = time.time()
        params = _get_request_data(request)
        if params.get('model_error'):
            return api_error(params['model_error'], 400, 'UNSUPPORTED_MODEL')
        params['model'] = ai_service.resolve_public_model(
            params['model'], DEFAULT_MODEL, allow_auto=False
        )
        if params.get('transcript_language_error'):
            return api_error(params['transcript_language_error'], 400)
        if params.get('enable_citations'):
            return api_error('스트리밍 생성은 인용 모드를 지원하지 않습니다. 일반 생성을 사용하세요.', 400)

        url = (params['url'] or '').strip()
        direct_content = params.get('content')
        has_direct_content = direct_content is not None and bool(direct_content.strip())
        request_data_all = request.get_json(silent=True) or {}

        if url and has_direct_content:
            return api_error('URL과 텍스트는 동시에 입력할 수 없습니다.', 400)

        is_direct_text = not url and direct_content is not None
        if is_direct_text:
            validation_error = _validate_direct_text_content(direct_content)
            if validation_error:
                return api_error(validation_error, 400)
        else:
            if not url:
                return api_error('YouTube URL이 필요합니다.', 400)
            if not content_service.is_youtube_url(url):
                return api_error('유효한 YouTube URL을 입력해주세요.', 400)

        video_id = None
        if not is_direct_text:
            video_id = content_service.get_video_id(url)
            if not video_id:
                return api_error('유효하지 않은 YouTube URL입니다.', 400)

        def _sse(payload):
            data = json.dumps(payload, ensure_ascii=False)
            return f"data: {data}\n\n"

        sse_headers = {
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }

        # 스트리밍 응답은 generator 종료까지 잠금과 선예약 수명을 직접 관리한다.
        user_id = getattr(g, 'user_id', None)
        usage_enabled = is_supabase_enabled() and bool(user_id)
        if usage_enabled:
            usage_lease = acquire_usage_request_lock(user_id)
            _ensure_usage_lease_valid(usage_lease)
        usage_reservation = UsageService.reserve_for_request(user_id)
        account_usage = usage_reservation.usage_after
        g.usage_reservation = usage_reservation
        g.usage = usage_reservation.usage_before
        g.updated_usage = None
        _ensure_usage_lease_valid(usage_lease)

        force = bool(request_data_all.get('force', False))
        cache_bypass = any((
            force,
            bool(user_id),
            bool(request_data_all.get('web_search', False)),
            bool(request_data_all.get('quality_check', False)),
        ))
        modifiers = params['modifiers'] or {}

        max_tokens = get_model_max_tokens(params['model'])
        cache_key = None
        source_type = None
        source_title = None
        source_meta = None

        if is_direct_text:
            source_type = 'text'
            source_title = '직접 입력 텍스트'
            comments = []
            raw_transcript = direct_content[:5000]
            transcript_source = 'direct_input'
            transcript_segments = []
            youtube_title = ''
            main_content = f"[사용자 입력 텍스트]\n{direct_content}"
            truncated_content = content_service.truncate_text(main_content, max_tokens)
            source_meta = {
                'source_type': 'text',
                'chars': len(direct_content),
                'quality_score': 1.0,
                'is_auto': False,
            }
        else:
            # 캐시 체크 — /generate와 동일한 키/force 의미론
            from services.core.cache_service import AICacheService
            from services.core.ai_prompt_context import get_prompt_context_cache_scope
            cache_style_prompt = _get_style_prompt(
                params['style'], params.get('custom_prompt')
            )
            cache_key = AICacheService.make_key(
                video_id, params['style'], params['model'],
                modifiers.get('length', 'medium'),
                modifiers.get('writing_style', 'conversational'),
                transcript_language=params.get('transcript_language'),
                context_scope=get_prompt_context_cache_scope(user_id),
                style_prompt=cache_style_prompt,
                modifiers=modifiers,
                detail_level=params.get('detail_level', 'standard'),
                web_search=bool(request_data_all.get('web_search', False)),
                agent_mode=False,
                analyze=False,
                output_format=params.get('output_format', 'html'),
                max_chars=params.get('max_chars'),
            )
            cache_resp = _handle_cache_hit(
                cache_key, cache_bypass, video_id, url, start_time,
                transcript_language=params.get('transcript_language'),
                on_cost_start=_start_stream_cost,
            )
            if cache_resp:
                cached_payload = cache_resp.get_json() or {}
                # 캐시 응답은 AI 비용이 없으므로 방금 만든 예약만 즉시 환불한다.
                _refund_stream_reservation(quiet=False)

                def cached_sse():
                    yield _sse({
                        'type': 'meta',
                        'youtube_title': cached_payload.get('youtube_title'),
                        'transcript_source': cached_payload.get('transcript_source'),
                    })
                    yield _sse({'type': 'result', **cached_payload})

                return Response(
                    stream_with_context(cached_sse()),
                    mimetype='text/event-stream',
                    headers=sse_headers,
                )

            youtube_title = content_service.get_content_title(
                url,
                on_cost_start=_start_stream_cost,
            ) or 'YouTube 영상'
            transcript_text, comments, error, raw_transcript, transcript_source, transcript_segments = _fetch_youtube_content(
                video_id,
                params.get('transcript_language'),
                _start_stream_cost,
            )
            if error:
                return api_error(error, 400)

            main_content = f"[영상 자막]\n{transcript_text}"
            truncated_content = content_service.truncate_text(main_content, max_tokens)

        style_prompt = _get_style_prompt(params['style'], params['custom_prompt'])
        model = params['model']
        web_search = bool(request_data_all.get('web_search', False))

        app = current_app._get_current_object()

        def generate_sse():
            with app.app_context():
                comment_future = None
                try:
                    # meta 이벤트
                    meta_event = {
                        'type': 'meta',
                        'transcript_source': transcript_source,
                    }
                    if is_direct_text:
                        meta_event.update({
                            'source_type': source_type,
                            'source_title': source_title,
                        })
                    else:
                        meta_event['youtube_title'] = youtube_title
                    yield _sse(meta_event)

                    # 댓글 요약/본문 스트림 중 어느 비용 작업도 예약 및 유효한
                    # 분산 임대보다 먼저 시작하지 못하게 마지막 경계를 확인한다.
                    _ensure_usage_lease_valid(usage_lease)
                    if comments:
                        # 댓글 요약은 메인 스트림과 병렬 실행해 result 전 공백을 줄입니다.
                        comment_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                        comment_future = comment_executor.submit(
                            _generate_comment_summary,
                            app,
                            comments,
                            model,
                            _start_stream_cost,
                        )
                        comment_executor.shutdown(wait=False)

                    # AI 본문 delta만 실시간 전송합니다.
                    full_content = ''
                    stream_meta = {}
                    _ensure_usage_lease_valid(usage_lease)
                    stream_iter = iter(ai_service.create_content_stream(
                        truncated_content, model, style_prompt,
                        modifiers=params['modifiers'], style_id=params['style'],
                        detail_level=params.get('detail_level'),
                        user_id=user_id,
                        web_search=web_search,
                        on_cost_start=_start_stream_cost,
                    ))
                    while True:
                        _ensure_usage_lease_valid(usage_lease)
                        try:
                            token = next(stream_iter)
                        except StopIteration as stop:
                            if isinstance(stop.value, dict):
                                stream_meta = stop.value
                            break
                        if token is None:
                            # 구버전 generator 호환
                            break

                        _ensure_usage_lease_valid(usage_lease)
                        full_content += token
                        yield _sse({
                            'type': 'delta',
                            'delta': token,
                        })

                    # 완료: 제목/본문 분리 + HTML 변환
                    title = source_title if is_direct_text else youtube_title
                    body = full_content
                    lines = full_content.split('\n')
                    if lines and lines[0].startswith('#'):
                        title = lines[0].lstrip('#').strip()
                        body = '\n'.join(lines[1:]).strip()

                    try:
                        html = md_lib.markdown(body, extensions=['tables', 'fenced_code', 'nl2br'])
                    except Exception:
                        html = f"<pre>{html_lib.escape(body)}</pre>"

                    usage = stream_meta.get('usage') or {
                        'prompt_tokens': 0,
                        'completion_tokens': 0,
                        'total_tokens': 0,
                    }
                    prompt = stream_meta.get('prompt') or ''
                    web_sources = stream_meta.get('web_sources')
                    comment_result = None

                    base_result = {
                        'title': title,
                        'content': body,
                        'html': html,
                        'usage': usage,
                    }
                    if comments:
                        # 댓글 요약은 스트리밍하지 않고, 메인 본문 완료 후 기존 방식으로 병합
                        yield _sse({'type': 'status', 'stage': 'comment_summary'})
                        if comment_future is not None:
                            try:
                                comment_result = comment_future.result()
                            except UsageLockUnavailable:
                                raise
                            except Exception as comment_err:
                                current_app.logger.warning(f"댓글 요약 생성 실패 (무시): {comment_err}")
                                comment_result = None
                        else:
                            # 예외적 경로: comment_future 생성 전 실패한 경우 메인 완료 후 순차 실행
                            comment_result = _generate_comment_summary(
                                app,
                                comments,
                                model,
                                _start_stream_cost,
                            )
                        base_result, prompt = _combine_results(base_result, prompt, comment_result)
                        title = base_result.get('title') or title
                        body = base_result.get('content') or body
                        html = base_result.get('html') or html
                        usage = base_result.get('usage') or usage

                    # 메타데이터 추출 — 비스트리밍 /generate와 동일하게 채워 회귀 방지
                    style = params['style']
                    seo = ai_service.extract_seo_metadata(body) if style == 'blog_seo' else None
                    faq_schema = (
                        ai_service.extract_faq_schema(body)
                        if style in ('blog_seo', 'geo_seo') else None
                    )
                    cta = ai_service.extract_cta(body) if style == 'geo_seo' else None

                    result = _apply_output_format(
                        base_result,
                        params.get('output_format', 'html'),
                        params.get('max_chars'),
                    )

                    result_event = {
                        'type': 'result',
                        **result,
                        'id': str(uuid.uuid4()),
                        'data': result.get('html', ''),
                        'elapsed_time': round(time.time() - start_time, 2),
                        'youtube_title': youtube_title,
                        'transcript': raw_transcript,
                        'transcript_source': transcript_source,
                        'style_label': _get_style_label(params['style']),
                        'cached': False,
                        'comment_summary_included': bool(comments and comment_result),
                        'seo': seo,
                        'geo': ai_service.extract_geo_metadata(body) if style == 'geo_seo' else None,
                        'faq_schema': faq_schema,
                        'cta': cta,
                        'json_ld_schemas': None,
                        'quality_score': None,
                        'web_sources': web_sources,
                        'analysis': None,
                        'transcript_segments': transcript_segments or [],
                        'chapters': [],
                        'total_duration_seconds': 0,
                        'quota': account_usage or get_usage_for_response(),
                    }
                    if is_direct_text:
                        result_event.update({
                            'source_type': source_type,
                            'source_title': source_title,
                            'source_meta': source_meta,
                        })
                        if user_id:
                            save_history(user_id, {
                                'id': result_event['id'],
                                'url': '',
                                'title': result.get('title') or source_title,
                                'style': params['style'],
                                'content': result.get('content', ''),
                                'html': result.get('html', ''),
                                'transcript': raw_transcript,
                                'transcript_source': 'direct_input',
                                'usage': result.get('usage'),
                                'elapsed_time': result_event['elapsed_time'],
                            })
                    else:
                        _persist_generation_result(
                            cache_key, video_id, params, url, youtube_title,
                            base_result, prompt, comment_result,
                            raw_transcript, transcript_source, comments,
                            result_event['elapsed_time'], result_event['id'],
                            user_id=user_id,
                        )

                    # DB 예약은 첫 비용 작업 직전에 이미 최종 사용으로 확정됐다.
                    # 성공 뒤 별도 RPC를 호출하지 않고 직렬화된 결과만 전송한다.
                    serialized_result_event = _sse(result_event)
                    yield serialized_result_event

                except Exception as e:
                    # 스트림 실패 시 미시작 댓글 요약은 취소해 불필요한 AI 호출 방지
                    if comment_future is not None:
                        comment_future.cancel()
                    safe_message = safe_error_or_fallback(
                        e,
                        '생성 중 오류가 발생했습니다. 다시 시도해주세요.',
                    )
                    yield _sse({
                        'type': 'error',
                        'error': safe_message,
                        'message': safe_message,
                    })
                finally:
                    if comment_future is not None and not comment_future.done():
                        comment_future.cancel()
                    if not stream_state['settled']:
                        _refund_stream_reservation(quiet=True)
                    if usage_lease is not None:
                        _release_usage_lease(usage_lease)

        response = Response(
            stream_with_context(generate_sse()),
            mimetype='text/event-stream',
            headers=sse_headers,
        )
        if usage_lease is not None:
            # generator가 소비되지 않거나 응답이 조기 종료되면 비용 성공으로
            # 확정되지 않은 자신의 예약을 환불하고 임대를 해제한다.
            def _close_stream_response():
                if not stream_state['settled']:
                    _refund_stream_reservation(quiet=True)
                _release_usage_lease(usage_lease)

            response.call_on_close(_close_stream_response)
            usage_lease_owned_by_response = True
        return response

    except InvalidIdempotencyKey as e:
        return api_error(str(e), 400, 'INVALID_IDEMPOTENCY_KEY')
    except (InvalidIdempotencyReplay, UsageReservationReplay) as e:
        response = {
            'error': str(e),
            'code': 'IDEMPOTENCY_REPLAY',
        }
        if isinstance(e, UsageReservationReplay):
            response['usage'] = e.usage
        return jsonify(response), 409
    except QuotaExceeded:
        return jsonify({
            'error': '오늘 사용 가능 횟수를 모두 소진했습니다.',
            'code': 'USAGE_LIMIT_EXCEEDED',
            'usage': {
                'usage_count': 0,
                'max_usage': MAX_USAGE_COUNT,
                'can_use': False,
            },
        }), 429
    except UsageLockBusy:
        return jsonify({
            'error': '이 계정의 콘텐츠 생성 요청이 이미 진행 중입니다.',
            'code': 'USAGE_REQUEST_IN_PROGRESS',
        }), 409
    except UsageLockUnavailable as e:
        current_app.logger.error('Generate stream usage lock unavailable: %s', e)
        return jsonify({
            'error': '사용량 확인 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.',
            'code': 'USAGE_LOCK_UNAVAILABLE',
        }), 503
    except UsageAccountingUnavailable as e:
        current_app.logger.error('Generate stream usage accounting unavailable: %s', e)
        return api_error(
            '사용량 기록 서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요.',
            503,
            'USAGE_ACCOUNTING_UNAVAILABLE',
        )
    except Exception as e:
        current_app.logger.error(f"Generate stream setup failed: {e}")
        return _handle_error_response(str(e))
    finally:
        if usage_lease is not None and not usage_lease_owned_by_response:
            if not stream_state['settled']:
                _refund_stream_reservation(quiet=True)
            _release_usage_lease(usage_lease)


@blog_bp.route('/api/video-qa', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def video_qa():
    """YouTube 영상 자막 기반 Q&A 챗봇 엔드포인트.

    요청 형식:
        {"video_url": str, "question": str, "history": [{"role": str, "content": str}], "model": str}

    응답 형식:
        {"answer": str, "sources": [{"text": str, "relevance": float}]}
    """
    from services.media.video_qa_service import (
        is_video_indexed,
        index_video_transcript,
        answer_question,
    )

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return api_error('JSON 객체가 필요합니다.', 400)

    raw_video_url = data.get('video_url', '')
    raw_question = data.get('question', '')
    if not isinstance(raw_video_url, str) or not isinstance(raw_question, str):
        return api_error('video_url과 question은 문자열이어야 합니다.', 400)
    video_url = raw_video_url.strip()
    question = raw_question.strip()

    history, history_error = _validate_video_qa_history(data.get('history', []))
    if history_error:
        return api_error(history_error, 400)

    from services.core.ai_service import resolve_public_model
    from services.media.video_qa_service import DEFAULT_QA_MODEL
    try:
        model = resolve_public_model(
            data.get('model'), DEFAULT_QA_MODEL, allow_auto=False
        )
    except ValueError as exc:
        return api_error(str(exc), 400, 'UNSUPPORTED_MODEL')

    # 입력값 검증
    if not video_url:
        return api_error('video_url이 필요합니다.', 400)
    if len(video_url) > VIDEO_QA_MAX_URL_CHARS:
        return api_error(f'video_url은 {VIDEO_QA_MAX_URL_CHARS}자 이내여야 합니다.', 400)
    if not content_service.is_youtube_url(video_url):
        return api_error('유효한 YouTube URL을 입력해주세요.', 400)
    if not question:
        return api_error('질문을 입력해주세요.', 400)
    if len(question) > VIDEO_QA_MAX_QUESTION_CHARS:
        return api_error(
            f'질문은 {VIDEO_QA_MAX_QUESTION_CHARS}자 이내로 입력해주세요.', 400
        )

    video_id = content_service.get_video_id(video_url)
    if not video_id:
        return api_error('영상 ID를 추출할 수 없습니다.', 400)

    try:
        on_cost_start = capture_usage_charge_callback()
        # 아직 인덱싱이 안 됐으면 자막을 가져와 인덱싱
        if not is_video_indexed(video_id):
            transcript_result = content_service.get_transcript(
                video_id,
                on_cost_start=on_cost_start,
            )

            # get_transcript 반환값은 str 또는 dict
            if isinstance(transcript_result, dict):
                if transcript_result.get('error'):
                    return api_error(sanitize_error_for_client(transcript_result['error']), 400)
                transcript_text = transcript_result.get('text') or transcript_result.get('transcript', '')
            elif isinstance(transcript_result, str):
                transcript_text = transcript_result
            else:
                transcript_text = ''

            if not transcript_text:
                return api_error('영상 자막을 가져올 수 없습니다.', 400)

            ok = index_video_transcript(video_id, transcript_text)
            if not ok:
                return api_error('[서버 오류] 영상 자막 인덱싱에 실패했습니다.', 500)

        # Q&A 답변 생성
        result = answer_question(
            video_id=video_id,
            question=question,
            history=history,
            model=model,
            on_cost_start=on_cost_start,
        )

        # 관련 청크가 없어 공급자에 진입하지 않은 성공 안내 응답은
        # 무비용 경로다. 실제 공급자가 시작됐다면 callback이 이미 확정했다.
        charge_state = getattr(g, 'usage_charge_state', None)
        if charge_state is not None and not charge_state.committed:
            g.skip_usage_decrement = True

        return jsonify(result)
    except UsageLockUnavailable:
        raise
    except Exception as exc:
        current_app.logger.error('Video QA failed: %s', exc, exc_info=True)
        return api_error_from_exception(exc, '[서버 오류] 영상 Q&A 처리 중 문제가 발생했습니다.')


@blog_bp.route('/api/tts', methods=['POST'])
@limiter.limit("20/minute")
@require_auth
@require_usage
def text_to_speech():
    """텍스트를 TTS(Text-to-Speech)로 변환해 MP3 오디오 파일을 반환합니다.

    요청 형식:
        {"text": str, "voice": str (optional), "speed": float (optional)}

    응답:
        audio/mpeg 파일 스트림
    """
    from config import TTS_DEFAULT_VOICE, TTS_MAX_CHARS
    from services.media.tts_service import TTSService

    data = request.get_json(silent=True) or {}

    text = (data.get('text') or '').strip()
    if not text:
        return api_error('변환할 텍스트를 입력하세요.', 400)

    if len(text) > TTS_MAX_CHARS:
        return jsonify({
            'error': f'텍스트가 너무 깁니다. 최대 {TTS_MAX_CHARS}자까지 지원합니다.'
        }), 400

    voice = data.get('voice') or TTS_DEFAULT_VOICE
    if not isinstance(voice, str):
        voice = TTS_DEFAULT_VOICE

    speed = data.get('speed', 1.0)
    try:
        speed = float(speed)
        speed = max(0.5, min(2.0, speed))
    except (TypeError, ValueError):
        speed = 1.0

    try:
        audio_bytes = TTSService.synthesize(
            text,
            voice=voice,
            speed=speed,
            preprocess=True,
            on_cost_start=capture_usage_charge_callback(),
        )
    except UsageLockUnavailable:
        raise
    except ValueError as exc:
        return handle_error(str(exc))
    except RuntimeError as exc:
        return api_error_from_exception(exc, '오디오 생성에 실패했습니다.')

    return Response(
        audio_bytes,
        mimetype='audio/mpeg',
        headers={
            'Content-Disposition': 'inline; filename="podcast.mp3"',
            'Content-Length': str(len(audio_bytes)),
            'Cache-Control': 'no-cache',
        },
    )


# =============================================
# 이벤트 추출
# =============================================

@blog_bp.route('/api/extract-events', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def extract_events_endpoint():
    """YouTube 영상 자막에서 구조화된 이벤트를 추출합니다.

    요청 형식:
        {"url": "https://youtube.com/..."} — URL 제공 시 자막 자동 추출
        {"transcript": "자막 텍스트"} — 자막 직접 제공
        {"model": "cliproxyapi/gpt-5.5"} — 서버 허용 목록 내 선택

    응답 형식:
        {"events": [...], "summary": {...}, "categorized": {...}}
    """
    data = request.get_json(silent=True) or {}

    url = (data.get('url') or '').strip()
    transcript_text = (data.get('transcript') or '').strip()
    from services.core.ai_service import resolve_public_model
    try:
        model = resolve_public_model(data.get('model'), DEFAULT_MODEL)
    except ValueError as exc:
        return api_error(str(exc), 400)
    on_cost_start = capture_usage_charge_callback()

    # 자막 획득: transcript 직접 제공 또는 URL에서 추출
    if not transcript_text:
        if not url:
            return api_error('url 또는 transcript 중 하나를 제공해야 합니다.', 400)

        if not content_service.is_youtube_url(url):
            return api_error('유효한 YouTube URL이 아닙니다.', 400)

        video_id = content_service.get_video_id(url)
        if not video_id:
            return api_error('YouTube 비디오 ID를 추출할 수 없습니다.', 400)

        try:
            transcript_data = content_service.get_transcript(
                video_id,
                on_cost_start=on_cost_start,
            )
            if isinstance(transcript_data, dict):
                transcript_value = transcript_data.get('text') or transcript_data.get('transcript', '')
            elif isinstance(transcript_data, str):
                transcript_value = transcript_data
                transcript_data = {}
            else:
                transcript_value = ''

            if not transcript_value:
                return api_error('영상 자막을 추출할 수 없습니다. 자막이 없는 영상이거나 접근 불가합니다.', 422)

            # 자막 세그먼트 → 타임스탬프 포함 텍스트 변환 (이벤트 추출 품질 향상)
            segments = transcript_data.get('segments', [])
            if segments:
                from services.core.ai_service import format_transcript_with_timestamps
                transcript_text = format_transcript_with_timestamps(segments)
            else:
                transcript_text = transcript_value

        except UsageLockUnavailable:
            raise
        except Exception as exc:
            return api_error_from_exception(exc, '자막 추출에 실패했습니다.')

    # 이벤트 추출
    try:
        from services.content.event_extraction_service import (
            extract_events, categorize_events, get_event_summary
        )
        event_kwargs = {'model': model}
        if callable(on_cost_start):
            event_kwargs['on_cost_start'] = on_cost_start
        events = extract_events(transcript_text, **event_kwargs)
        categorized = categorize_events(events)
        summary = get_event_summary(events)

        return jsonify({
            'events': events,
            'categorized': categorized,
            'summary': summary,
        })

    except UsageLockUnavailable:
        raise
    except ValueError as exc:
        return handle_error(str(exc))
    except RuntimeError as exc:
        return api_error_from_exception(exc, '이벤트 추출에 실패했습니다.')
    except Exception as exc:
        return api_error_from_exception(exc, '이벤트 추출 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')

# ============================================================
# 분리된 라우트 패키지 — 부수효과 import로 자동 등록
# - routes/blog/templates.py: 프롬프트 템플릿 5개
# ============================================================
from routes import blog as _blog_subroutes  # noqa: E402,F401
