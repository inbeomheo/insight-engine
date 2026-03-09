"""
타임코드 포함 영상 Q&A 강화 서비스

기존 video_qa_service와 달리 외부 API/ChromaDB 없이 동작하며,
자막 키워드 매칭 기반으로 타임코드가 포함된 답변을 생성합니다.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class TimecodeRef:
    """답변 근거가 되는 타임코드 참조 정보."""
    timestamp: str      # "MM:SS" 형식
    text: str            # 해당 구간의 자막 텍스트
    relevance: float     # 0.0 ~ 1.0


@dataclass
class QAResponse:
    """타임코드 포함 Q&A 응답 결과."""
    question: str
    answer: str
    timecodes: List[TimecodeRef]
    confidence: float    # 0.0 ~ 1.0 (전체 답변 신뢰도)


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


def _extract_keywords(question: str) -> List[str]:
    """질문에서 검색 키워드를 추출합니다.

    불용어(stopwords)를 제외하고 2글자 이상인 단어만 반환합니다.
    """
    # 한국어 기본 불용어
    stopwords = {
        '이', '그', '저', '것', '수', '등', '더', '를', '을', '에', '의',
        '가', '는', '은', '도', '로', '으로', '와', '과', '에서', '까지',
        '무엇', '어떻게', '왜', '어디', '언제', '누가', '뭐', '어떤',
        '이것', '그것', '있는', '하는', '되는', '인가', '인지',
    }
    words = question.strip().split()
    return [w for w in words if len(w) >= 2 and w.lower() not in stopwords]


def _calculate_sentence_relevance(sentence: str, keywords: List[str]) -> float:
    """문장과 키워드 목록 간의 관련도를 계산합니다."""
    if not keywords:
        return 0.0
    sentence_lower = sentence.lower()
    matched = sum(1 for kw in keywords if kw.lower() in sentence_lower)
    return round(matched / len(keywords), 3)


def _build_answer(matched_sentences: List[str], question: str) -> str:
    """매칭된 문장들을 기반으로 답변 텍스트를 생성합니다."""
    if not matched_sentences:
        return "해당 질문과 관련된 내용을 영상에서 찾을 수 없습니다."

    # 상위 3개 문장으로 답변 구성
    top_sentences = matched_sentences[:3]
    answer_parts = []
    for i, sentence in enumerate(top_sentences, 1):
        answer_parts.append(f"{i}. {sentence}")

    return "영상에서 관련 내용을 찾았습니다:\n" + "\n".join(answer_parts)


def qa_with_timecodes(
    video_id: str,
    question: str,
    transcript: str = '',
) -> QAResponse:
    """자막에서 질문 관련 구간을 검색하여 타임코드 포함 답변을 생성합니다.

    Args:
        video_id: YouTube 영상 ID
        question: 사용자 질문
        transcript: 영상 자막 텍스트

    Returns:
        QAResponse — 답변 + 타임코드 참조 + 신뢰도
    """
    if not question or not question.strip():
        logger.warning("빈 질문 — 기본 응답 반환 (video_id=%s)", video_id)
        return QAResponse(
            question=question or "",
            answer="질문을 입력해 주세요.",
            timecodes=[],
            confidence=0.0,
        )

    if not transcript or not transcript.strip():
        logger.info("빈 자막 — 답변 불가 (video_id=%s)", video_id)
        return QAResponse(
            question=question,
            answer="영상 자막이 없어 답변할 수 없습니다.",
            timecodes=[],
            confidence=0.0,
        )

    keywords = _extract_keywords(question)
    if not keywords:
        # 키워드 추출 실패 시 질문 전체를 단일 키워드로 사용
        keywords = [question.strip()]

    sentences = _split_sentences(transcript)
    if not sentences:
        return QAResponse(
            question=question,
            answer="자막을 분석할 수 없습니다.",
            timecodes=[],
            confidence=0.0,
        )

    # 문장별 관련도 계산
    scored_items: List[tuple] = []  # (index, sentence, score)
    for idx, sentence in enumerate(sentences):
        score = _calculate_sentence_relevance(sentence, keywords)
        if score > 0.0:
            scored_items.append((idx, sentence, score))

    # 관련도 내림차순 정렬
    scored_items.sort(key=lambda x: x[2], reverse=True)

    # 상위 결과로 타임코드 참조 생성
    timecodes: List[TimecodeRef] = []
    matched_sentences: List[str] = []

    for idx, sentence, score in scored_items[:5]:
        timestamp = _format_timestamp(idx * 10)
        timecodes.append(TimecodeRef(
            timestamp=timestamp,
            text=sentence,
            relevance=score,
        ))
        matched_sentences.append(sentence)

    answer = _build_answer(matched_sentences, question)

    # 전체 신뢰도: 상위 매칭 점수의 가중 평균
    if timecodes:
        confidence = round(
            sum(tc.relevance for tc in timecodes) / len(timecodes), 3
        )
    else:
        confidence = 0.0

    result = QAResponse(
        question=question,
        answer=answer,
        timecodes=timecodes,
        confidence=confidence,
    )

    logger.info(
        "Q&A 완료 (video_id=%s, 매칭=%d건, 신뢰도=%.3f)",
        video_id, len(timecodes), confidence,
    )
    return result
