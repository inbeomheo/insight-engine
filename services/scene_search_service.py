"""
자연어 장면 검색 서비스

자막(transcript) 텍스트에서 자연어 쿼리를 기반으로
관련 장면(구간)을 검색합니다. 외부 API 없이 키워드 매칭으로 동작합니다.
"""
from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

# 장면 기본 길이(초)
DEFAULT_SCENE_DURATION = 15


@dataclass
class SceneResult:
    """검색된 장면 결과를 나타내는 데이터 클래스."""
    scene_id: str
    video_id: str
    timestamp: str          # "MM:SS" 형식
    description: str        # 장면 설명 (매칭된 자막)
    relevance_score: float  # 0.0 ~ 1.0
    duration_seconds: int   # 장면 길이(초)


def _format_timestamp(seconds: int) -> str:
    """초 단위를 MM:SS 형식 문자열로 변환합니다."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


def _split_sentences(transcript: str) -> List[str]:
    """자막 텍스트를 문장 단위로 분리합니다."""
    if not transcript or not transcript.strip():
        return []
    sentences = re.split(r'[.\n!?]+', transcript)
    return [s.strip() for s in sentences if s.strip()]


def _extract_query_keywords(query: str) -> List[str]:
    """쿼리에서 검색 키워드를 추출합니다.

    1글자 이하 단어 및 기본 불용어를 제외합니다.
    """
    stopwords = {
        '이', '그', '저', '것', '수', '등', '더', '를', '을', '에', '의',
        '가', '는', '은', '도', '로', '으로', '와', '과', '에서', '까지',
        '찾아', '보여', '줘', '주세요', '어디', '있나', '나오는',
    }
    words = query.strip().split()
    return [w for w in words if len(w) >= 2 and w.lower() not in stopwords]


def _calculate_relevance(sentence: str, keywords: List[str]) -> float:
    """문장과 키워드 간 관련도를 계산합니다."""
    if not keywords:
        return 0.0
    sentence_lower = sentence.lower()
    matched = sum(1 for kw in keywords if kw.lower() in sentence_lower)
    return round(matched / len(keywords), 3)


def _estimate_duration(sentence: str) -> int:
    """문장 길이에 따라 장면 길이(초)를 추정합니다.

    짧은 문장은 기본값, 긴 문장은 비례적으로 증가합니다.
    """
    char_count = len(sentence)
    if char_count < 20:
        return 10
    if char_count < 50:
        return DEFAULT_SCENE_DURATION
    return min(30, DEFAULT_SCENE_DURATION + (char_count - 50) // 10)


def search_scenes(
    video_id: str,
    query: str,
    transcript: str = '',
) -> List[SceneResult]:
    """자막에서 쿼리와 관련된 장면을 검색합니다.

    쿼리의 키워드를 자막 문장과 매칭하여 관련도 0.3 이상인
    장면만 반환합니다. 결과는 관련도 내림차순으로 정렬됩니다.

    Args:
        video_id: YouTube 영상 ID
        query: 자연어 검색 쿼리
        transcript: 영상 자막 텍스트

    Returns:
        관련 장면 목록 (빈 자막/쿼리이면 빈 리스트)
    """
    if not transcript or not transcript.strip():
        logger.info("빈 자막 — 장면 검색 건너뜀 (video_id=%s)", video_id)
        return []

    if not query or not query.strip():
        logger.warning("빈 쿼리 — 장면 검색 건너뜀 (video_id=%s)", video_id)
        return []

    keywords = _extract_query_keywords(query)
    if not keywords:
        # 키워드 추출 실패 시 쿼리 전체를 단일 키워드로 사용
        keywords = [query.strip()]

    sentences = _split_sentences(transcript)
    if not sentences:
        return []

    results: List[SceneResult] = []

    for idx, sentence in enumerate(sentences):
        score = _calculate_relevance(sentence, keywords)
        if score < 0.3:
            continue

        start_sec = idx * 10
        duration = _estimate_duration(sentence)

        scene = SceneResult(
            scene_id=uuid.uuid4().hex[:12],
            video_id=video_id,
            timestamp=_format_timestamp(start_sec),
            description=sentence,
            relevance_score=score,
            duration_seconds=duration,
        )
        results.append(scene)

    # 관련도 내림차순 정렬
    results.sort(key=lambda s: s.relevance_score, reverse=True)

    logger.info(
        "장면 검색 완료 (video_id=%s, query='%s', 결과=%d건)",
        video_id, query[:30], len(results),
    )
    return results
