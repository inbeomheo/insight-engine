"""챕터 자동 분할 서비스"""
import json
import re
from services.core import ai_service
from prompts.styles.chapter_split import CHAPTER_SPLIT_PROMPT


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


def _format_time(seconds):
    """초를 HH:MM:SS 형식으로 변환"""
    h = int(seconds) // 3600
    m = (int(seconds) % 3600) // 60
    s = int(seconds) % 60
    if h > 0:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'
