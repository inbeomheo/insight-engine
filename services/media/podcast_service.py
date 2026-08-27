"""
팟캐스트 에피소드 자동 생성 서비스

콘텐츠를 2인 대화체 스크립트로 변환 후 TTS로 MP3를 생성합니다.
"""
import logging
from typing import Callable, Dict, Optional

from services.core import ai_service
from services.media.tts_service import TTSService, EDGE_VOICE_KO
from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)

# 팟캐스트 스크립트 생성 프롬프트
PODCAST_SCRIPT_PROMPT = """당신은 팟캐스트 스크립트 작가입니다.
아래 콘텐츠를 2인 대화 형식의 팟캐스트 스크립트로 변환하세요.

규칙:
1. 진행자(Host)와 게스트(Guest) 두 명이 대화합니다
2. 자연스러운 구어체로 작성 (실제 팟캐스트처럼)
3. 각 발화는 "Host:" 또는 "Guest:" 접두사로 시작
4. 인사/도입 → 핵심 내용 논의 → 정리/마무리 구성
5. 총 8-15개 발화 단위로 구성
6. 콘텐츠에 있는 정보만 사용 (창작/추측 금지)

출력 형식 (각 줄):
Host: (발화 내용)
Guest: (발화 내용)
"""

# 호스트/게스트 목소리 (Edge TTS)
VOICE_HOST = 'ko-KR-InJoonNeural'   # 남성
VOICE_GUEST = EDGE_VOICE_KO          # 여성


def _generate_script(
    content: str,
    title: str,
    model: str,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> str:
    """AI로 팟캐스트 대화 스크립트를 생성합니다."""
    input_text = f"[제목] {title}\n\n[콘텐츠]\n{content[:8000]}"
    result = ai_service.create_content(
        input_text,
        model,
        PODCAST_SCRIPT_PROMPT,
        on_cost_start=on_cost_start,
    )
    return result.get('content', '')


def _parse_script(script_text: str):
    """스크립트를 (speaker, text) 튜플 목록으로 파싱합니다."""
    lines = []
    for line in script_text.strip().split('\n'):
        line = line.strip()
        if line.startswith('Host:'):
            lines.append(('host', line[5:].strip()))
        elif line.startswith('Guest:'):
            lines.append(('guest', line[6:].strip()))
    return lines


def _synthesize_podcast(
    parsed_lines,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> bytes:
    """파싱된 스크립트를 TTS로 합성 후 MP3 바이트로 반환합니다."""
    chunks = []
    for speaker, text in parsed_lines:
        if not text.strip():
            continue
        voice = VOICE_HOST if speaker == 'host' else VOICE_GUEST
        try:
            audio_bytes = TTSService.synthesize(
                text,
                voice=voice,
                preprocess=False,
                on_cost_start=on_cost_start,
            )
            chunks.append(audio_bytes)
        except UsageLockUnavailable:
            raise
        except Exception as exc:
            logger.warning(
                'TTS 합성 실패 (speaker=%s, type=%s)',
                speaker,
                type(exc).__name__,
            )
            continue

    if not chunks:
        raise RuntimeError('모든 TTS 합성이 실패했습니다.')

    # MP3 청크 연결 (단순 바이트 연결 — MP3 스트림은 청크 연결 가능)
    return b''.join(chunks)


def generate_podcast_episode(
    content: str,
    title: str,
    model: str = '',
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Dict:
    """콘텐츠에서 팟캐스트 에피소드를 생성합니다.

    Args:
        content: 원본 콘텐츠 (마크다운)
        title: 에피소드 제목
        model: AI 모델 ID
        on_cost_start: AI·TTS 공급자 호출 직전에 실행할 콜백

    Returns:
        {
            "script": str,         # 대화 스크립트 텍스트
            "audio_base64": str,   # MP3 오디오 (base64)
            "duration_estimate": int  # 예상 길이(초)
        }

    Raises:
        ValueError: 콘텐츠가 비어 있음
        RuntimeError: 스크립트 생성 또는 TTS 실패
    """
    import base64

    if not content or not content.strip():
        raise ValueError('팟캐스트로 변환할 콘텐츠가 필요합니다.')

    if not model:
        from routes.blog_routes import DEFAULT_MODEL
        model = DEFAULT_MODEL
    model = ai_service.resolve_public_model(model, allow_auto=False)

    # 1. 스크립트 생성
    script = _generate_script(
        content,
        title,
        model,
        on_cost_start=on_cost_start,
    )
    if not script.strip():
        raise RuntimeError('팟캐스트 스크립트 생성 결과가 비어 있습니다.')

    # 2. 스크립트 파싱
    parsed = _parse_script(script)
    if len(parsed) < 2:
        raise RuntimeError('유효한 대화가 2개 미만입니다. 스크립트 생성을 다시 시도해 주세요.')

    # 3. TTS 합성
    audio_bytes = _synthesize_podcast(
        parsed,
        on_cost_start=on_cost_start,
    )

    # 4. 예상 길이 (한국어 약 3~4글자/초 기준)
    total_chars = sum(len(text) for _, text in parsed)
    duration_estimate = max(30, total_chars // 3)

    return {
        'script': script,
        'audio_base64': base64.b64encode(audio_bytes).decode('ascii'),
        'duration_estimate': duration_estimate,
    }
