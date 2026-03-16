"""브랜드 보이스 프로파일러 서비스.

콘텐츠의 브랜드 보이스(톤, 문체, 어휘 수준)를 규칙 기반으로 분석합니다.
AI API 호출 없이 순수 텍스트 분석만 사용합니다.
"""

import logging
import re
import statistics
from typing import Optional


logger = logging.getLogger(__name__)

# --- 패턴 상수 ---

# 격식체 어미
_FORMAL_ENDINGS = re.compile(r'(?:습니다|합니다|입니다|됩니다)[.?!]?\s*$')

# 비격식체 어미
_CASUAL_ENDINGS = re.compile(r'(?:해요|죠|거든요|잖아요|네요)[.?!]?\s*$')

# 평서형 어미
_PLAIN_ENDINGS = re.compile(r'(?:다|이다)[.?!]?\s*$')

# 영어 단어
_ENGLISH_WORD = re.compile(r'[A-Za-z]{2,}')

# 접속사 (한국어는 \b 사용 불가 — 조사 결합으로 경계 불명확)
_CONJUNCTIONS = re.compile(r'(?<![가-힣])(?:그리고|또한|하지만|그러나|따라서|그러므로)(?![가-힣])')

# 부사절
_SUBORDINATE_CLAUSES = re.compile(r'(?:하면|할\s*때|하므로|하기\s*때문에)')

# 감정 표현 단어
_EMOTION_WORDS = re.compile(r'(?:정말|매우|너무|엄청|굉장히|놀랍게도)')

# 이모티콘/특수문자
_EMOTICONS = re.compile(r'[ㅋㅎ]{2,}|\^\^|[~]{2,}')

# 강조 표현 (마크다운 볼드, 대문자 영어)
_EMPHASIS = re.compile(r'\*\*[^*]+\*\*|[A-Z]{3,}')

# 숫자 패턴
_NUMBER_PATTERN = re.compile(r'\d+')

# 문장 분리 (마침표, 물음표, 느낌표 기준 — 종결 부호 보존)
_SENTENCE_FIND = re.compile(r'[^.!?\n]+[.!?]*')

# 단락 분리
_PARAGRAPH_SPLIT = re.compile(r'\n\s*\n')


def _split_sentences(content: str) -> list[str]:
    """콘텐츠를 문장 단위로 분리합니다 (종결 부호 보존)."""
    raw = _SENTENCE_FIND.findall(content)
    return [s.strip() for s in raw if s.strip()]


def _split_words(content: str) -> list[str]:
    """콘텐츠를 단어 단위로 분리합니다."""
    return content.split()


def _calc_formality_score(sentences: list[str]) -> float:
    """격식도 점수를 계산합니다 (0-100)."""
    if not sentences:
        return 50.0

    total = len(sentences)
    formal_count = sum(1 for s in sentences if _FORMAL_ENDINGS.search(s))
    casual_count = sum(1 for s in sentences if _CASUAL_ENDINGS.search(s))

    # 격식체 비율 × 100
    score = (formal_count / total) * 100

    # 비격식체 발견 시 -20씩
    score -= casual_count * 20

    return max(0.0, min(100.0, score))


def _calc_vocabulary_complexity(words: list[str]) -> float:
    """어휘 복잡도를 계산합니다 (0-100)."""
    if not words:
        return 0.0

    # 1. 평균 단어 길이 기여 (한국어 2-3자 보통, 4자+ 복잡)
    avg_len = sum(len(w) for w in words) / len(words)
    # 2자 → 0점, 4자+ → 40점 범위
    length_score = min(40.0, max(0.0, (avg_len - 2) * 20))

    # 2. 영어/전문용어 비율
    english_count = sum(1 for w in words if _ENGLISH_WORD.match(w))
    english_ratio = (english_count / len(words)) * 100
    english_score = min(30.0, english_ratio * 3)

    # 3. 한자어 비율 추정 (4음절+ 한국어 단어)
    korean_words = [w for w in words if not _ENGLISH_WORD.match(w)]
    long_korean = sum(1 for w in korean_words if len(w) >= 4)
    hanja_ratio = (long_korean / len(words)) * 100 if words else 0
    hanja_score = min(30.0, hanja_ratio * 2)

    return min(100.0, length_score + english_score + hanja_score)


def _calc_sentence_complexity(sentences: list[str], content: str) -> float:
    """문장 복잡도를 계산합니다 (0-100)."""
    if not sentences:
        return 0.0

    # 1. 평균 문장 길이 기여 (20자 기준, 40자+ → 높음)
    avg_sent_len = sum(len(s) for s in sentences) / len(sentences)
    length_score = min(40.0, max(0.0, (avg_sent_len - 10) * 1.3))

    # 2. 접속사 빈도
    conj_count = len(_CONJUNCTIONS.findall(content))
    conj_score = min(30.0, (conj_count / max(1, len(sentences))) * 30)

    # 3. 부사절 빈도
    sub_count = len(_SUBORDINATE_CLAUSES.findall(content))
    sub_score = min(30.0, (sub_count / max(1, len(sentences))) * 30)

    return min(100.0, length_score + conj_score + sub_score)


def _calc_emotional_intensity(sentences: list[str], content: str) -> float:
    """감정 강도를 계산합니다 (0-100)."""
    if not sentences:
        return 0.0

    total = len(sentences)
    score = 0.0

    # 1. 감탄사/감정 표현 빈도
    emotion_count = len(_EMOTION_WORDS.findall(content))
    score += min(35.0, (emotion_count / max(1, total)) * 50)

    # 2. 느낌표 빈도
    excl_count = content.count('!')
    score += min(25.0, (excl_count / max(1, total)) * 35)

    # 3. 이모티콘/특수문자 빈도
    emoticon_count = len(_EMOTICONS.findall(content))
    score += min(20.0, emoticon_count * 10)

    # 4. 강조 표현 빈도
    emphasis_count = len(_EMPHASIS.findall(content))
    score += min(20.0, emphasis_count * 8)

    return min(100.0, score)


def _calc_consistency_score(sentences: list[str], content: str) -> float:
    """문체 일관성 점수를 계산합니다 (0-100)."""
    if len(sentences) < 2:
        return 100.0

    score = 100.0

    # 1. 문장 길이 표준편차 (낮을수록 높은 점수)
    lengths = [len(s) for s in sentences]
    if len(lengths) >= 2:
        stdev = statistics.stdev(lengths)
        mean = statistics.mean(lengths)
        cv = (stdev / mean) if mean > 0 else 0  # 변동계수
        # 변동계수 0 → 감점 0, 변동계수 1+ → 감점 30
        score -= min(30.0, cv * 30)

    # 2. 어미 패턴 일관성 (같은 유형의 어미 비율)
    formal = sum(1 for s in sentences if _FORMAL_ENDINGS.search(s))
    casual = sum(1 for s in sentences if _CASUAL_ENDINGS.search(s))
    plain = sum(1 for s in sentences if _PLAIN_ENDINGS.search(s))
    dominant = max(formal, casual, plain)
    ending_ratio = dominant / len(sentences)
    # 지배적 어미 비율이 높을수록 일관적
    # 비율 1.0 → 감점 0, 비율 0.3 → 감점 35
    score -= max(0.0, (1.0 - ending_ratio) * 50)

    # 3. 단락 길이 균일성
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(content) if p.strip()]
    if len(paragraphs) >= 2:
        para_lengths = [len(p) for p in paragraphs]
        para_stdev = statistics.stdev(para_lengths)
        para_mean = statistics.mean(para_lengths)
        para_cv = (para_stdev / para_mean) if para_mean > 0 else 0
        score -= min(20.0, para_cv * 20)

    return max(0.0, min(100.0, score))


def _determine_formality(formality_score: float) -> str:
    """격식도 레이블을 결정합니다."""
    if formality_score >= 70:
        return "formal"
    elif formality_score >= 40:
        return "neutral"
    else:
        return "casual"


def _determine_tone(
    formality_score: float,
    vocabulary_complexity: float,
    sentence_complexity: float,
    emotional_intensity: float,
) -> str:
    """톤을 결정합니다 (우선순위: professional > authoritative > educational > friendly > conversational)."""
    if formality_score >= 70 and emotional_intensity < 30:
        return "professional"
    if formality_score >= 70 and vocabulary_complexity >= 70:
        return "authoritative"
    if vocabulary_complexity >= 60 and sentence_complexity >= 60:
        return "educational"
    if 40 <= formality_score < 70 and emotional_intensity >= 40:
        return "friendly"
    if formality_score < 40 and emotional_intensity >= 50:
        return "conversational"
    return "neutral"


def _determine_energy(emotional_intensity: float, sentences: list[str]) -> str:
    """에너지 레벨을 결정합니다."""
    # 감탄문 비율
    excl_sentences = sum(1 for s in sentences if '!' in s)
    excl_ratio = (excl_sentences / len(sentences) * 100) if sentences else 0

    if emotional_intensity >= 60 or excl_ratio >= 10:
        return "high"
    elif emotional_intensity >= 30:
        return "medium"
    else:
        return "low"


def _detect_characteristics(
    formality_score: float,
    emotional_intensity: float,
    sentences: list[str],
    words: list[str],
    content: str,
) -> list[str]:
    """문체 특성을 감지합니다."""
    chars = []

    # 격식/비격식 판별
    if formality_score >= 70:
        chars.append("격식체 중심")
    elif formality_score < 40:
        chars.append("비격식체 중심")
    else:
        chars.append("혼합 문체")

    # 문장 길이
    if sentences:
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        if avg_len <= 20:
            chars.append("짧은 문장 선호")
        elif avg_len >= 40:
            chars.append("긴 문장 선호")

    # 전문용어
    if words:
        english_count = sum(1 for w in words if _ENGLISH_WORD.match(w))
        if (english_count / len(words)) * 100 >= 10:
            chars.append("전문용어 다수")

    # 감정적 표현
    if emotional_intensity >= 60:
        chars.append("감정적 표현 풍부")

    # 질문형 구조
    if sentences:
        question_count = sum(1 for s in sentences if '?' in s)
        if (question_count / len(sentences)) * 100 >= 10:
            chars.append("질문형 구조")

    # 데이터 중심
    if sentences:
        data_count = sum(1 for s in sentences if _NUMBER_PATTERN.search(s))
        if (data_count / len(sentences)) * 100 >= 20:
            chars.append("데이터 중심")

    return chars


def _detect_dominant_patterns(
    sentences: list[str],
    words: list[str],
    content: str,
    characteristics: list[str],
) -> list[str]:
    """주요 패턴을 감지합니다 (상위 3개)."""
    patterns: list[tuple[str, float]] = []

    if sentences:
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        if avg_len <= 20:
            patterns.append(("짧은 문장 선호", 20 - avg_len))
        elif avg_len >= 40:
            patterns.append(("긴 문장 선호", avg_len - 40))

    # 질문형
    if sentences:
        q_ratio = sum(1 for s in sentences if '?' in s) / len(sentences)
        if q_ratio >= 0.05:
            patterns.append(("질문형 구조", q_ratio * 100))

    # 리스트/열거형
    list_markers = len(re.findall(r'(?:^|\n)\s*[-•·]\s', content))
    numbered = len(re.findall(r'(?:^|\n)\s*\d+[.)]\s', content))
    list_count = list_markers + numbered
    if list_count >= 2:
        patterns.append(("리스트/열거형 구조", list_count * 5.0))

    # 접속사 다용
    conj_count = len(_CONJUNCTIONS.findall(content))
    if conj_count >= 2:
        patterns.append(("접속사 다용", conj_count * 3.0))

    # 강조 표현 사용
    emphasis_count = len(_EMPHASIS.findall(content))
    if emphasis_count >= 1:
        patterns.append(("강조 표현 사용", emphasis_count * 5.0))

    # 반복 어미
    if sentences:
        formal_count = sum(1 for s in sentences if _FORMAL_ENDINGS.search(s))
        if formal_count / len(sentences) >= 0.6:
            patterns.append(("격식체 어미 반복", (formal_count / len(sentences)) * 20))

    # 느낌표 다용
    excl_count = content.count('!')
    if excl_count >= 3:
        patterns.append(("느낌표 다용", excl_count * 3.0))

    # 점수 높은 순 정렬, 상위 3개
    patterns.sort(key=lambda x: x[1], reverse=True)
    return [p[0] for p in patterns[:3]]


def _generate_suggestions(
    formality: str,
    tone: str,
    energy: str,
    metrics: dict,
    characteristics: list[str],
) -> list[str]:
    """개선 제안을 생성합니다."""
    suggestions = []

    # 일관성 낮으면
    if metrics["consistency_score"] < 60:
        suggestions.append("문체 일관성을 높이기 위해 동일한 어미 패턴을 유지하세요.")

    # 감정 강도 너무 높으면
    if metrics["emotional_intensity"] > 70:
        suggestions.append("감정 표현을 줄이면 전문성이 높아집니다.")

    # 감정 강도 너무 낮으면
    if metrics["emotional_intensity"] < 20:
        suggestions.append("적절한 감정 표현을 추가하면 독자 참여도가 높아집니다.")

    # 어휘 복잡도 높으면
    if metrics["vocabulary_complexity"] > 70:
        suggestions.append("전문용어 사용을 줄이면 더 많은 독자가 이해할 수 있습니다.")

    # 문장 복잡도 높으면
    if metrics["sentence_complexity"] > 70:
        suggestions.append("문장을 짧게 나누면 가독성이 향상됩니다.")

    # 문장 복잡도 너무 낮으면
    if metrics["sentence_complexity"] < 20:
        suggestions.append("문장 간 연결어를 활용하면 논리적 흐름이 개선됩니다.")

    # 혼합 문체
    if "혼합 문체" in characteristics:
        suggestions.append("격식체와 비격식체를 혼용하지 않으면 통일감이 높아집니다.")

    # 제안이 없으면 기본 제안
    if not suggestions:
        suggestions.append("현재 문체가 일관적이고 균형 잡혀 있습니다.")

    return suggestions


_EMPTY_PROFILE = {
    "voice_profile": {
        "formality": "neutral",
        "tone": "neutral",
        "energy": "low",
    },
    "metrics": {
        "formality_score": 50.0,
        "vocabulary_complexity": 0.0,
        "sentence_complexity": 0.0,
        "emotional_intensity": 0.0,
        "consistency_score": 100.0,
    },
    "characteristics": [],
    "dominant_patterns": [],
    "suggestions": [],
}


def _compute_all_metrics(sentences: list, words: list, content: str) -> dict:
    """모든 브랜드 보이스 메트릭을 계산합니다.

    Returns:
        각 메트릭의 원시값 dict (반올림 전)
    """
    return {
        "formality_score": _calc_formality_score(sentences),
        "vocabulary_complexity": _calc_vocabulary_complexity(words),
        "sentence_complexity": _calc_sentence_complexity(sentences, content),
        "emotional_intensity": _calc_emotional_intensity(sentences, content),
        "consistency_score": _calc_consistency_score(sentences, content),
    }


def profile_brand_voice(content: Optional[str]) -> dict:
    """콘텐츠의 브랜드 보이스를 분석하여 프로파일을 반환합니다.

    Args:
        content: 분석할 텍스트 콘텐츠

    Returns:
        voice_profile, metrics, characteristics, dominant_patterns, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_PROFILE, "suggestions": ["분석할 콘텐츠가 충분하지 않습니다."]}
    try:

        content = content.strip()
        sentences = _split_sentences(content)
        words = _split_words(content)

        raw = _compute_all_metrics(sentences, words, content)
        formality = _determine_formality(raw["formality_score"])
        tone = _determine_tone(
            raw["formality_score"], raw["vocabulary_complexity"],
            raw["sentence_complexity"], raw["emotional_intensity"]
        )
        energy = _determine_energy(raw["emotional_intensity"], sentences)

        metrics = {k: round(v, 1) for k, v in raw.items()}
        characteristics = _detect_characteristics(
            raw["formality_score"], raw["emotional_intensity"], sentences, words, content
        )

        return {
            "voice_profile": {"formality": formality, "tone": tone, "energy": energy},
            "metrics": metrics,
            "characteristics": characteristics,
            "dominant_patterns": _detect_dominant_patterns(sentences, words, content, characteristics),
            "suggestions": _generate_suggestions(formality, tone, energy, metrics, characteristics),
        }
    except Exception as e:
        logger.error(f"브랜드 보이스 분석 처리 실패: {e}")
        return {**_EMPTY_PROFILE, "suggestions": ["분석 중 오류가 발생했습니다."]}
