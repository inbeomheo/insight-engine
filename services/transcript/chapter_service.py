"""챕터 자동 분할 서비스"""
import json
import re
from services.core import ai_service
from prompts.styles.chapter_split import CHAPTER_SPLIT_PROMPT
import logging

logger = logging.getLogger(__name__)


def split_chapters(transcript_text: str, model: str, segments: list = None) -> list:
    """자막 텍스트를 AI로 분석하여 챕터 목록을 반환합니다.

    Args:
        transcript_text: 자막 전체 텍스트
        model: AI 모델 ID
        segments: 타임스탬프 포함 세그먼트 (있으면 사용)

    Returns:
        [{'title': str, 'start': int, 'end': int, 'summary': str}, ...]
    """
    # 세그먼트가 있으면 타임스탬프 포함 텍스트 구성
    if segments:
        content = '\n'.join([
            f'[{_format_time(s["start"])}] {s["text"]}'
            for s in segments
        ])
    else:
        content = transcript_text

    # 텍스트가 너무 짧으면 챕터 분할 불필요
    if len(content) < 500:
        return []

    try:
        result = ai_service.create_content(
            content, model, CHAPTER_SPLIT_PROMPT, style_id='summary'
        )
        raw = result.get('content', '')
        # JSON 추출
        json_match = re.search(r'\{[\s\S]*\}', raw)
        if json_match:
            data = json.loads(json_match.group())
            chapters = data.get('chapters', [])
            # 유효성 검증
            return [
                ch for ch in chapters
                if isinstance(ch.get('title'), str)
                and isinstance(ch.get('start'), (int, float))
                and isinstance(ch.get('end'), (int, float))
            ]
    except Exception:
        pass
    return []


def get_total_duration(segments: list) -> int:
    """세그먼트 목록에서 총 영상 길이(초)를 추정합니다.

    마지막 세그먼트의 start + 평균 세그먼트 간격으로 계산.

    Args:
        segments: [{'start': float, 'text': str}, ...]

    Returns:
        총 길이(초). 세그먼트가 없으면 0.
    """
    if not segments:
        return 0
    starts = [s.get('start', 0) for s in segments if isinstance(s.get('start'), (int, float))]
    if not starts:
        return 0
    if len(starts) == 1:
        return int(starts[0]) + 10  # 단일 세그먼트: 시작 + 여유 10초
    # 평균 세그먼트 간격을 마지막 세그먼트에 더함
    avg_gap = (max(starts) - min(starts)) / (len(starts) - 1)
    return int(max(starts) + avg_gap)


def _format_time(seconds):
    """초를 HH:MM:SS 형식으로 변환"""
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    if h > 0:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'
