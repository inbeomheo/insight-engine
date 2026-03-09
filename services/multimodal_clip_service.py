"""
멀티모달 클립 추출 서비스

프롬프트 기반으로 자막(transcript)에서 관련 클립 구간을 추출합니다.
키워드 매칭으로 타임스탬프를 시뮬레이션하며, 외부 API 호출 없이 동작합니다.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class ClipResult:
    """추출된 클립 결과를 나타내는 데이터 클래스."""
    clip_id: str
    video_id: str
    start_time: str      # "MM:SS" 형식
    end_time: str         # "MM:SS" 형식
    relevance_score: float  # 0.0 ~ 1.0
    matched_text: str     # 매칭된 자막 텍스트


def _format_timestamp(seconds: int) -> str:
    """초 단위를 MM:SS 형식 문자열로 변환합니다."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def _split_sentences(transcript: str) -> List[str]:
    """자막 텍스트를 문장 단위로 분리합니다."""
    if not transcript or not transcript.strip():
        return []
    # 줄바꿈 또는 마침표/물음표/느낌표 기준 분리
    sentences = re.split(r'[.\n!?]+', transcript)
    return [s.strip() for s in sentences if s.strip()]


def _calculate_relevance(sentence: str, keywords: List[str]) -> float:
    """문장 내 키워드 매칭 비율로 관련도 점수를 계산합니다.

    Args:
        sentence: 대상 문장
        keywords: 검색 키워드 목록

    Returns:
        0.0 ~ 1.0 사이의 관련도 점수
    """
    if not keywords:
        return 0.0
    sentence_lower = sentence.lower()
    matched = sum(1 for kw in keywords if kw.lower() in sentence_lower)
    return round(matched / len(keywords), 3)


def extract_by_prompt(
    video_id: str,
    prompt: str,
    transcript: str = '',
) -> List[ClipResult]:
    """프롬프트 기반으로 자막에서 관련 클립 구간을 추출합니다.

    프롬프트의 키워드를 자막 문장과 매칭하여 관련도가 높은 구간을
    클립으로 추출합니다. 관련도 0.3 이상인 결과만 반환합니다.

    Args:
        video_id: YouTube 영상 ID
        prompt: 검색 프롬프트 (공백 구분 키워드)
        transcript: 영상 자막 텍스트

    Returns:
        관련도 순으로 정렬된 ClipResult 리스트 (빈 자막이면 빈 리스트)
    """
    if not transcript or not transcript.strip():
        logger.info("빈 자막 — 클립 추출 건너뜀 (video_id=%s)", video_id)
        return []

    if not prompt or not prompt.strip():
        logger.warning("빈 프롬프트 — 클립 추출 건너뜀 (video_id=%s)", video_id)
        return []

    keywords = [w for w in prompt.strip().split() if w]
    sentences = _split_sentences(transcript)

    if not sentences:
        return []

    # 문장별 예상 길이(초): 전체 자막을 균등 분할
    total_duration = len(sentences) * 10  # 문장당 약 10초로 추정
    results: List[ClipResult] = []

    for idx, sentence in enumerate(sentences):
        score = _calculate_relevance(sentence, keywords)
        if score < 0.3:
            continue

        start_sec = idx * 10
        end_sec = min(start_sec + 10, total_duration)

        clip = ClipResult(
            clip_id=uuid.uuid4().hex[:12],
            video_id=video_id,
            start_time=_format_timestamp(start_sec),
            end_time=_format_timestamp(end_sec),
            relevance_score=score,
            matched_text=sentence,
        )
        results.append(clip)

    # 관련도 내림차순 정렬
    results.sort(key=lambda c: c.relevance_score, reverse=True)

    logger.info(
        "클립 추출 완료 (video_id=%s, prompt='%s', 결과=%d건)",
        video_id, prompt[:30], len(results),
    )
    return results
