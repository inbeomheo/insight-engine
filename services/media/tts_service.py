"""
TTS (Text-to-Speech) 서비스

블로그 콘텐츠를 오디오로 변환합니다.
백엔드 우선순위:
  1. OpenAI TTS (OPENAI_API_KEY 설정 시)
  2. Edge TTS (무료 폴백, edge-tts 패키지)
"""
import asyncio
import io
import logging
import os
import re

from config import TTS_BACKEND, TTS_DEFAULT_VOICE, TTS_MAX_CHARS

logger = logging.getLogger(__name__)

# OpenAI TTS 지원 목소리 목록
OPENAI_VOICES = {'alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer'}

# Edge TTS 한국어 기본 목소리
EDGE_VOICE_KO = 'ko-KR-SunHiNeural'
EDGE_VOICE_EN = 'en-US-AriaNeural'

# 마크다운 → 텍스트 변환용 정규식 (사전 컴파일)
_RE_CODE_BLOCK = re.compile(r'```[\s\S]*?```', re.MULTILINE)
_RE_INLINE_CODE = re.compile(r'`[^`]+`')
_RE_IMAGE = re.compile(r'!\[.*?\]\(.*?\)')
_RE_LINK = re.compile(r'\[([^\]]+)\]\([^\)]+\)')
_RE_HEADING = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_RE_BOLD_ITALIC = re.compile(r'\*{1,3}([^\*]+)\*{1,3}')
_RE_STRIKETHROUGH = re.compile(r'~~([^~]+)~~')
_RE_BLOCKQUOTE = re.compile(r'^>\s+', re.MULTILINE)
_RE_HR = re.compile(r'^[-*_]{3,}\s*$', re.MULTILINE)
_RE_TABLE_ROW = re.compile(r'\|.*?\|', re.MULTILINE)
_RE_TABLE_SEP = re.compile(r'^\|[-| :]+\|$', re.MULTILINE)
_RE_BULLET = re.compile(r'^[\s]*[-*+]\s+', re.MULTILINE)
_RE_ORDERED = re.compile(r'^[\s]*\d+\.\s+', re.MULTILINE)
_RE_MULTI_NEWLINE = re.compile(r'\n{3,}')
_RE_WHITESPACE = re.compile(r'[ \t]+')


def preprocess_for_tts(markdown_text: str) -> str:
    """마크다운 텍스트를 TTS에 적합한 평문으로 변환합니다.

    Args:
        markdown_text: 마크다운 형식의 텍스트

    Returns:
        음성 출력에 적합한 평문 텍스트
    """
    text = markdown_text

    # 코드 블록 제거 (내용 포함)
    text = _RE_CODE_BLOCK.sub('', text)
    # 인라인 코드 제거
    text = _RE_INLINE_CODE.sub('', text)
    # 이미지 제거
    text = _RE_IMAGE.sub('', text)
    # 링크 → 링크 텍스트만 유지
    text = _RE_LINK.sub(r'\1', text)
    # 제목 기호 제거 (텍스트는 유지)
    text = _RE_HEADING.sub('', text)
    # 볼드/이탤릭 기호 제거 (텍스트는 유지)
    text = _RE_BOLD_ITALIC.sub(r'\1', text)
    # 취소선 제거 (텍스트는 유지)
    text = _RE_STRIKETHROUGH.sub(r'\1', text)
    # 블록쿼트 기호 제거
    text = _RE_BLOCKQUOTE.sub('', text)
    # 수평선 제거
    text = _RE_HR.sub('', text)
    # 표 구분자 행 제거
    text = _RE_TABLE_SEP.sub('', text)
    # 표 셀 구분자 제거 (내용은 유지)
    text = _RE_TABLE_ROW.sub(lambda m: m.group(0).replace('|', ' '), text)
    # 불릿 기호를 자연스러운 흐름으로 변환
    text = _RE_BULLET.sub('', text)
    # 순서 목록 기호 제거
    text = _RE_ORDERED.sub('', text)
    # 연속 빈 줄 정리
    text = _RE_MULTI_NEWLINE.sub('\n\n', text)
    # 연속 공백 정리
    text = _RE_WHITESPACE.sub(' ', text)

    return text.strip()


def _select_backend() -> str:
    """사용 가능한 TTS 백엔드를 자동 선택합니다."""
    if TTS_BACKEND == 'openai':
        return 'openai'
    if TTS_BACKEND == 'edge':
        return 'edge'
    # auto: OpenAI 키가 있으면 OpenAI, 없으면 Edge
    if os.getenv('OPENAI_API_KEY'):
        return 'openai'
    return 'edge'


def _synthesize_openai(text: str, voice: str, speed: float) -> bytes:
    """OpenAI TTS API로 오디오를 생성합니다.

    Args:
        text: 음성으로 변환할 텍스트
        voice: 목소리 (alloy/echo/fable/onyx/nova/shimmer)
        speed: 속도 (0.25~4.0)

    Returns:
        MP3 오디오 바이트
    """
    import httpx

    api_key = os.getenv('OPENAI_API_KEY', '')
    if not api_key:
        raise RuntimeError('OPENAI_API_KEY가 설정되지 않았습니다.')

    safe_voice = voice if voice in OPENAI_VOICES else TTS_DEFAULT_VOICE
    safe_speed = max(0.25, min(4.0, speed))

    payload = {
        'model': 'tts-1',
        'input': text,
        'voice': safe_voice,
        'speed': safe_speed,
        'response_format': 'mp3',
    }

    with httpx.Client(timeout=60, follow_redirects=False) as client:
        resp = client.post(
            'https://api.openai.com/v1/audio/speech',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json=payload,
        )

    status_code = getattr(resp, 'status_code', 0)
    if isinstance(status_code, int) and 300 <= status_code < 400:
        raise RuntimeError(f'OpenAI TTS API 리다이렉트 차단: {resp.status_code}')

    if resp.status_code != 200:
        raise RuntimeError(f'OpenAI TTS API 오류: {resp.status_code} {resp.text[:200]}')

    return resp.content


def _synthesize_edge(text: str, voice: str, speed: float) -> bytes:
    """Edge TTS (무료)로 오디오를 생성합니다.

    Args:
        text: 음성으로 변환할 텍스트
        voice: Edge TTS 목소리 이름
        speed: 속도 배율 (0.5~2.0 → rate 파라미터로 변환)

    Returns:
        MP3 오디오 바이트
    """
    try:
        import edge_tts
    except ImportError as exc:
        raise RuntimeError(
            'edge-tts 패키지가 설치되지 않았습니다. '
            '"pip install edge-tts>=6.1.0" 실행 후 재시도하세요.'
        ) from exc

    # Edge TTS 목소리 결정: 목소리 이름이 nn-CC-XxxNeural 형식이면 그대로 사용
    edge_voice = voice if re.match(r'^[a-z]{2}-[A-Z]{2}-\w+', voice) else EDGE_VOICE_KO

    # 속도 변환: 1.0 → +0%, 1.5 → +50%, 0.5 → -50%
    rate_pct = int((speed - 1.0) * 100)
    rate_str = f'{rate_pct:+d}%'

    async def _run() -> bytes:
        buf = io.BytesIO()
        communicate = edge_tts.Communicate(text, edge_voice, rate=rate_str)
        async for chunk in communicate.stream():
            if chunk['type'] == 'audio':
                buf.write(chunk['data'])
        return buf.getvalue()

    try:
        loop = asyncio.new_event_loop()
        audio_bytes = loop.run_until_complete(_run())
    finally:
        loop.close()

    if not audio_bytes:
        raise RuntimeError('Edge TTS가 오디오를 생성하지 못했습니다.')

    return audio_bytes


def _split_text(text: str, max_chars: int) -> list[str]:
    """텍스트를 문장 경계에서 분할합니다.

    마침표/물음표/느낌표 뒤 공백을 기준으로 분할하여
    문장이 중간에 잘리지 않도록 합니다.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        # max_chars 이내에서 마지막 문장 경계 찾기
        split_pos = -1
        for sep in ['. ', '? ', '! ', '。', '\n\n', '\n']:
            pos = remaining.rfind(sep, 0, max_chars)
            if pos > split_pos:
                split_pos = pos + len(sep)

        # 문장 경계를 못 찾으면 공백에서 분할
        if split_pos <= 0:
            split_pos = remaining.rfind(' ', 0, max_chars)
        # 공백도 없으면 강제 분할
        if split_pos <= 0:
            split_pos = max_chars

        chunks.append(remaining[:split_pos].rstrip())
        remaining = remaining[split_pos:].lstrip()

    return [c for c in chunks if c.strip()]


def _synthesize_with_fallback(backend: str, text: str, voice: str, speed: float) -> bytes:
    """TTS 합성을 시도하고 OpenAI 실패 시 Edge로 폴백합니다."""
    try:
        if backend == 'openai':
            return _synthesize_openai(text, voice, speed)
        return _synthesize_edge(text, voice, speed)
    except Exception as exc:
        logger.error('TTS 합성 실패 (backend=%s): %s', backend, exc)
        if backend == 'openai':
            logger.info('OpenAI TTS 실패 → Edge TTS로 폴백')
            return _synthesize_edge(text, EDGE_VOICE_KO, speed)
        raise


class TTSService:
    """TTS 합성 서비스.

    synthesize() 메서드 하나로 백엔드 선택을 추상화합니다.
    """

    @staticmethod
    def synthesize(
        text: str,
        voice: str = TTS_DEFAULT_VOICE,
        speed: float = 1.0,
        preprocess: bool = True,
    ) -> bytes:
        """텍스트를 오디오(MP3)로 변환합니다.

        Args:
            text: 변환할 텍스트 (마크다운 포함 가능)
            voice: 목소리 식별자
            speed: 재생 속도 (0.5 ~ 2.0)
            preprocess: True면 마크다운을 평문으로 전처리

        Returns:
            MP3 포맷의 오디오 바이트

        Raises:
            ValueError: 텍스트가 비어 있거나 길이 초과
            RuntimeError: TTS 백엔드 오류
        """
        if not text or not text.strip():
            raise ValueError('변환할 텍스트를 입력하세요.')

        if preprocess:
            text = preprocess_for_tts(text)

        if not text.strip():
            raise ValueError('전처리 후 텍스트가 비어 있습니다.')

        backend = _select_backend()

        # 장문 분할 처리: TTS_MAX_CHARS 초과 시 청크로 나눠 합성 후 합치기
        if len(text) > TTS_MAX_CHARS:
            logger.info('TTS 장문 분할: %d자 → %d자 단위 청크', len(text), TTS_MAX_CHARS)
            chunks = _split_text(text, TTS_MAX_CHARS)
            audio_parts = []
            for idx, chunk in enumerate(chunks):
                logger.info('TTS 청크 %d/%d 합성 중 (%d자)', idx + 1, len(chunks), len(chunk))
                part = _synthesize_with_fallback(backend, chunk, voice, speed)
                audio_parts.append(part)
            return b''.join(audio_parts)

        logger.info('TTS 합성 시작: backend=%s, chars=%d, voice=%s', backend, len(text), voice)
        return _synthesize_with_fallback(backend, text, voice, speed)
