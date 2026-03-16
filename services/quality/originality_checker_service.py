"""독창성·출처 중복 검사 서비스 — 순수 규칙 기반 (n-gram, Jaccard 유사도)"""
import logging
import re


logger = logging.getLogger(__name__)

# 한국어 클리셰 사전
CLICHE_PHRASES = [
    "오늘날 빠르게 변화하는",
    "다양한 분야에서 활용",
    "많은 사람들이",
    "최근 들어",
    "이러한 관점에서",
    "그렇다면 어떻게",
    "결론적으로 말하자면",
    "아시다시피",
    "주목할 만한 것은",
    "흥미로운 점은",
    "중요한 것은",
    "말할 것도 없이",
    "두말할 나위 없이",
    "과언이 아니다",
    "심심치 않게",
]

# 내부 반복 유사도 임계값
SELF_REPEAT_THRESHOLD = 0.5
# 외부 중복 유사도 임계값
EXTERNAL_OVERLAP_THRESHOLD = 0.6


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리한다."""
    # 마크다운 헤딩, 빈 줄 제거 후 문장 분리
    cleaned = re.sub(r'^#{1,6}\s+.*$', '', text, flags=re.MULTILINE)
    sentences = re.split(r'[.!?。\n]+', cleaned)
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def _tokenize(sentence: str) -> set[str]:
    """문장을 단어 집합으로 변환한다."""
    words = re.findall(r'[가-힣]+|[a-zA-Z]+|[0-9]+', sentence)
    return set(words)


def _jaccard_similarity(a: set, b: set) -> float:
    """두 집합의 Jaccard 유사도를 계산한다."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def _detect_self_repetition(sentences: list[str]) -> tuple[float, list[dict]]:
    """내부 반복 문장을 감지한다.

    Returns:
        (반복률 0-100, 플래그된 문장 목록)
    """
    if len(sentences) < 2:
        return 0.0, []

    flagged = []
    repeated_indices = set()
    tokenized = [_tokenize(s) for s in sentences]

    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences)):
            sim = _jaccard_similarity(tokenized[i], tokenized[j])
            if sim >= SELF_REPEAT_THRESHOLD:
                repeated_indices.add(i)
                repeated_indices.add(j)
                # 나중 문장을 플래그 (앞 문장이 원본)
                if j not in {f.get("_index") for f in flagged}:
                    flagged.append({
                        "sentence": sentences[j],
                        "issue": "self_repeat",
                        "similarity": round(sim, 3),
                        "matched_with": sentences[i],
                        "_index": j,
                    })

    # 내부 인덱스 제거
    for f in flagged:
        f.pop("_index", None)

    repetition_rate = (len(repeated_indices) / len(sentences)) * 100
    return round(repetition_rate, 2), flagged


def _detect_external_overlap(
    sentences: list[str],
    reference_contents: list[dict],
) -> tuple[float, list[dict]]:
    """외부 참조 콘텐츠와의 중복을 감지한다.

    Returns:
        (중복률 0-100, 플래그된 문장 목록)
    """
    if not reference_contents:
        return 0.0, []

    # 참조 문장들 준비
    ref_sentences = []
    for ref in reference_contents:
        ref_content = ref.get("content", "")
        ref_title = ref.get("title", ref.get("id", "unknown"))
        for s in _split_sentences(ref_content):
            ref_sentences.append((s, ref_title))

    if not ref_sentences:
        return 0.0, []

    flagged = []
    overlapped_count = 0
    tokenized_main = [_tokenize(s) for s in sentences]
    tokenized_refs = [(_tokenize(rs), rs, rt) for rs, rt in ref_sentences]

    for i, main_tokens in enumerate(tokenized_main):
        best_sim = 0.0
        best_ref_sentence = ""
        best_ref_title = ""
        for ref_tokens, ref_sent, ref_title in tokenized_refs:
            sim = _jaccard_similarity(main_tokens, ref_tokens)
            if sim > best_sim:
                best_sim = sim
                best_ref_sentence = ref_sent
                best_ref_title = ref_title

        if best_sim >= EXTERNAL_OVERLAP_THRESHOLD:
            overlapped_count += 1
            flagged.append({
                "sentence": sentences[i],
                "issue": "external_overlap",
                "similarity": round(best_sim, 3),
                "matched_with": f"[{best_ref_title}] {best_ref_sentence}",
            })

    overlap_rate = (overlapped_count / len(sentences)) * 100 if sentences else 0.0
    return round(overlap_rate, 2), flagged


def _detect_common_phrases(content: str) -> tuple[list[str], list[dict]]:
    """클리셰(진부한 표현)를 감지한다.

    Returns:
        (발견된 클리셰 목록, 플래그된 문장 목록)
    """
    found = []
    flagged = []
    for phrase in CLICHE_PHRASES:
        if phrase in content:
            found.append(phrase)
            flagged.append({
                "sentence": phrase,
                "issue": "common_phrase",
                "similarity": 1.0,
                "matched_with": "클리셰 사전",
            })
    return found, flagged


def _calculate_grade(score: float) -> str:
    """점수에 따른 등급을 반환한다."""
    if score >= 85:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 55:
        return "C"
    elif score >= 40:
        return "D"
    else:
        return "F"


def _generate_suggestions(
    self_repetition: float,
    external_overlap: float | None,
    common_phrases: list[str],
    unique_ratio: float,
) -> list[str]:
    """분석 결과에 따른 개선 제안을 생성한다."""
    suggestions = []

    if self_repetition > 20:
        suggestions.append("내부 반복 문장이 많습니다. 다양한 표현으로 바꿔보세요.")
    if self_repetition > 40:
        suggestions.append("문장 구조를 다양화하여 반복감을 줄이세요.")

    if external_overlap is not None and external_overlap > 30:
        suggestions.append("외부 콘텐츠와 중복되는 부분이 있습니다. 독자적인 관점을 추가하세요.")
    if external_overlap is not None and external_overlap > 50:
        suggestions.append("출처 콘텐츠와 유사도가 높습니다. 재구성이 필요합니다.")

    if len(common_phrases) >= 3:
        suggestions.append("클리셰 표현이 많습니다. 구체적이고 독창적인 표현으로 대체하세요.")
    elif len(common_phrases) >= 1:
        suggestions.append("일부 진부한 표현이 발견되었습니다. 더 신선한 표현을 사용해보세요.")

    if unique_ratio < 60:
        suggestions.append("고유 문장 비율이 낮습니다. 콘텐츠의 독창성을 높여보세요.")

    if not suggestions:
        suggestions.append("전반적으로 독창성이 높은 콘텐츠입니다.")

    return suggestions


def _analyze_all_overlaps(sentences: list, content: str,
                           reference_contents: list) -> tuple:
    """내부 반복, 외부 중복, 클리셰를 분석합니다.

    Returns:
        (self_repetition, self_flagged, external_overlap, external_flagged,
         common_phrases, cliche_flagged, unique_ratio)
    """
    self_repetition, self_flagged = _detect_self_repetition(sentences)

    external_overlap = None
    external_flagged = []
    if reference_contents:
        external_overlap, external_flagged = _detect_external_overlap(
            sentences, reference_contents
        )

    common_phrases, cliche_flagged = _detect_common_phrases(content)

    flagged_sentence_texts = set()
    for f in self_flagged:
        flagged_sentence_texts.add(f["sentence"])
    for f in external_flagged:
        flagged_sentence_texts.add(f["sentence"])
    unique_count = sum(1 for s in sentences if s not in flagged_sentence_texts)
    unique_ratio = round((unique_count / len(sentences)) * 100, 2)

    return (self_repetition, self_flagged, external_overlap, external_flagged,
            common_phrases, cliche_flagged, unique_ratio)


def _compute_originality_score(unique_ratio: float, self_repetition: float,
                                common_phrases: list) -> tuple:
    """독창성 점수와 등급을 계산합니다.

    Returns:
        (score, grade)
    """
    common_phrases_penalty = min(len(common_phrases) * 5, 50)
    score = (
        unique_ratio * 0.5
        + (100 - self_repetition) * 0.3
        + (100 - common_phrases_penalty) * 0.2
    )
    score = round(max(0.0, min(100.0, score)), 2)
    grade = _calculate_grade(score)
    return score, grade


def check_originality(content: str, reference_contents: list = None) -> dict:
    """콘텐츠의 독창성을 분석한다.

    Args:
        content: 분석할 콘텐츠 텍스트
        reference_contents: 비교 대상 목록
            [{"id": str, "title": str, "content": str}, ...]
            없으면 자체 분석만 수행 (내부 반복 검사)

    Returns:
        독창성 점수, 등급, 중복 분석, 플래그된 문장, 클리셰, 제안 목록
    """
    if not content or not content.strip():
        return {
            "originality_score": 0.0, "grade": "F",
            "overlap_analysis": {"self_repetition": 0.0, "external_overlap": None, "unique_ratio": 0.0},
            "flagged_sentences": [], "common_phrases": [],
            "suggestions": ["분석할 콘텐츠가 없습니다."],
        }

    try:
        sentences = _split_sentences(content)
        if not sentences:
            return {
                "originality_score": 50.0, "grade": "C",
                "overlap_analysis": {"self_repetition": 0.0,
                                     "external_overlap": None if not reference_contents else 0.0,
                                     "unique_ratio": 100.0},
                "flagged_sentences": [], "common_phrases": [],
                "suggestions": ["문장이 너무 짧아 정밀 분석이 어렵습니다."],
            }

        (self_repetition, self_flagged, external_overlap, external_flagged,
         common_phrases, cliche_flagged, unique_ratio) = (
            _analyze_all_overlaps(sentences, content, reference_contents)
        )

        originality_score, grade = _compute_originality_score(
            unique_ratio, self_repetition, common_phrases
        )

        suggestions = _generate_suggestions(
            self_repetition, external_overlap, common_phrases, unique_ratio
        )

        return {
            "originality_score": originality_score,
            "grade": grade,
            "overlap_analysis": {
                "self_repetition": self_repetition,
                "external_overlap": external_overlap,
                "unique_ratio": unique_ratio,
            },
            "flagged_sentences": self_flagged + external_flagged + cliche_flagged,
            "common_phrases": common_phrases,
            "suggestions": suggestions,
        }
    except Exception as e:
        logger.error(f"독창성 분석 처리 실패: {e}")
        return {"originality_score": 0.0, "grade": "F", "overlap_analysis": {}, "flagged_sentences": [], "common_phrases": [], "suggestions": ["분석 중 오류가 발생했습니다."]}
