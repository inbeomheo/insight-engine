"""
메시지 파편화 분석 서비스

다중 채널에서 발행되는 메시지의 일관성을 분석하고,
파편화된 메시지와 개선 권고를 제공합니다.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


@dataclass
class MessageFragment:
    """개별 메시지 파편 정보"""
    channel: str
    message_summary: str
    tone: str
    deviation_score: float


@dataclass
class FragmentationReport:
    """메시지 파편화 분석 보고서"""
    consistency_score: float
    fragments: List[MessageFragment] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# 톤 분류 키워드
_TONE_KEYWORDS: Dict[str, List[str]] = {
    "formal": ["드립니다", "하겠습니다", "바랍니다", "존경", "고객님", "안내", "말씀"],
    "casual": ["해요", "있어요", "거예요", "인데요", "ㅎㅎ", "ㅋㅋ", "꿀팁", "대박"],
    "urgent": ["긴급", "즉시", "지금", "서두", "마감", "한정", "놓치지"],
    "promotional": ["할인", "무료", "혜택", "이벤트", "특가", "프로모션", "쿠폰"],
    "informational": ["안내", "공지", "변경", "업데이트", "알림", "참고", "확인"],
}


def _detect_tone(text: str) -> str:
    """텍스트의 톤을 감지합니다."""
    scores: Dict[str, int] = {tone: 0 for tone in _TONE_KEYWORDS}

    for tone, keywords in _TONE_KEYWORDS.items():
        for kw in keywords:
            scores[tone] += len(re.findall(re.escape(kw), text))

    max_score = max(scores.values())
    if max_score == 0:
        return "neutral"

    return max(scores, key=lambda t: scores[t])


def _summarize_message(text: str, max_len: int = 80) -> str:
    """메시지를 요약합니다."""
    cleaned = text.strip().replace("\n", " ")
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[:max_len] + "..."


def _extract_keywords(text: str) -> Set[str]:
    """텍스트에서 주요 키워드를 추출합니다 (2자 이상 단어)."""
    # 한글/영문 단어 추출
    words = re.findall(r'[가-힣a-zA-Z]{2,}', text)
    return set(words)


def _calculate_deviation(
    msg_keywords: Set[str],
    all_keywords: Set[str],
    msg_tone: str,
    dominant_tone: str,
) -> float:
    """메시지의 전체 대비 이탈 점수를 계산합니다."""
    if not all_keywords:
        return 0.0

    # 키워드 유사도 (자카드)
    intersection = len(msg_keywords & all_keywords)
    union = len(msg_keywords | all_keywords)
    keyword_similarity = intersection / union if union > 0 else 0.0

    # 톤 일치 점수
    tone_match = 1.0 if msg_tone == dominant_tone else 0.0

    # 이탈 점수: 유사도가 낮고 톤이 다를수록 높음
    deviation = 1.0 - (keyword_similarity * 0.6 + tone_match * 0.4)
    return round(max(0.0, min(1.0, deviation)), 4)


def _generate_recommendations(
    fragments: List[MessageFragment],
    consistency_score: float,
) -> List[str]:
    """분석 결과에 기반한 개선 권고를 생성합니다."""
    recommendations: List[str] = []

    if consistency_score < 0.5:
        recommendations.append("채널 간 메시지 일관성이 낮습니다. 통합 메시지 가이드를 수립하세요.")

    # 톤 분산 확인
    tones = [f.tone for f in fragments]
    unique_tones = set(tones)
    if len(unique_tones) > 2:
        recommendations.append(
            f"톤이 {len(unique_tones)}가지로 분산되어 있습니다. "
            "채널별 톤 가이드를 통일하세요."
        )

    # 높은 이탈 메시지 경고
    high_deviation = [f for f in fragments if f.deviation_score > 0.7]
    if high_deviation:
        channels = ", ".join(f.channel for f in high_deviation)
        recommendations.append(
            f"다음 채널의 메시지가 크게 벗어나 있습니다: {channels}"
        )

    if not recommendations:
        recommendations.append("메시지 일관성이 양호합니다.")

    return recommendations


def analyze_fragmentation(messages: List[dict]) -> FragmentationReport:
    """다중 채널 메시지의 파편화를 분석합니다.

    Args:
        messages: 채널별 메시지 리스트.
            각 항목은 {"channel": str, "message": str} 형태.

    Returns:
        FragmentationReport: 일관성 점수, 파편 목록, 개선 권고.
    """
    if not messages:
        logger.warning("빈 메시지 데이터가 전달되었습니다.")
        return FragmentationReport(consistency_score=0.0)

    # 전체 키워드 풀 및 톤 빈도
    all_keywords: Set[str] = set()
    msg_data: List[dict] = []
    tone_counts: Dict[str, int] = {}

    for msg in messages:
        text = msg.get("message", "")
        channel = msg.get("channel", "unknown")
        keywords = _extract_keywords(text)
        tone = _detect_tone(text)
        summary = _summarize_message(text)

        all_keywords |= keywords
        tone_counts[tone] = tone_counts.get(tone, 0) + 1
        msg_data.append({
            "channel": channel,
            "text": text,
            "keywords": keywords,
            "tone": tone,
            "summary": summary,
        })

    # 지배적 톤 결정
    dominant_tone = max(tone_counts, key=lambda t: tone_counts[t]) if tone_counts else "neutral"

    # 파편화 분석
    fragments: List[MessageFragment] = []
    total_deviation = 0.0

    for data in msg_data:
        deviation = _calculate_deviation(
            data["keywords"], all_keywords, data["tone"], dominant_tone,
        )
        total_deviation += deviation
        fragments.append(MessageFragment(
            channel=data["channel"],
            message_summary=data["summary"],
            tone=data["tone"],
            deviation_score=deviation,
        ))

    # 일관성 점수: 1 - 평균 이탈 점수
    avg_deviation = total_deviation / len(fragments) if fragments else 0.0
    consistency_score = round(1.0 - avg_deviation, 4)

    # 이탈 점수 내림차순 정렬 (가장 파편화된 것 우선)
    fragments.sort(key=lambda f: f.deviation_score, reverse=True)

    recommendations = _generate_recommendations(fragments, consistency_score)

    logger.info(
        "메시지 파편화 분석 완료: %d개 채널, 일관성=%.2f",
        len(fragments), consistency_score,
    )

    return FragmentationReport(
        consistency_score=consistency_score,
        fragments=fragments,
        recommendations=recommendations,
    )
