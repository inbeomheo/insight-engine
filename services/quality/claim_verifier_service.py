"""
Claim & Citation Verifier 서비스

콘텐츠에서 사실 주장, 수치, 인용문을 자동 감지하고
출처 필요 여부를 규칙 기반으로 판단합니다 (AI API 호출 없음).
"""
import logging
import re
from typing import List, Dict, Optional


logger = logging.getLogger(__name__)

# ── 주장 감지 패턴 ──

# 통계 주장: 숫자 + 단위
_STAT_UNIT_PATTERN = re.compile(
    r'\d[\d,\.]*\s*(?:%|퍼센트|배|명|건|원|달러|조|억|만|천|개|회|件|件数)'
)
# "~에 따르면 N", "통계에 의하면"
_STAT_PHRASE_PATTERN = re.compile(
    r'(?:통계|조사|데이터|연구|보고서)에\s*(?:따르면|의하면|보면)'
)

# 사실 주장: 절대적 표현
_ABSOLUTE_EXPRESSIONS = re.compile(
    r'(?:최초|최대|최소|최고|최저|유일|세계\s*최초|역대\s*최|국내\s*최|사상\s*최)'
)
# "~년에 ~했다" 역사적 사실
_HISTORICAL_PATTERN = re.compile(
    r'(?:19|20)\d{2}년[에에는]?\s*.+(?:했다|되었다|시작했다|출시했다|설립했다|개발했다)'
)
# "~은 ~이다" 단정적 서술
_ASSERTIVE_PATTERN = re.compile(
    r'(?:은|는|이|가)\s+.{2,30}(?:이다|다)\s*[\.。]'
)

# 인용: 큰따옴표 텍스트
_QUOTE_PATTERN = re.compile(
    r'["\u201C]([^"\u201D]{4,})["\u201D]'
)
# "~라고 말했다/밝혔다"
_QUOTE_VERB_PATTERN = re.compile(
    r'(?:라고|라며|라면서)\s*(?:말했다|밝혔다|전했다|발표했다|언급했다|주장했다|설명했다|강조했다)'
)

# 비교 주장
_COMPARISON_PATTERN = re.compile(
    r'(?:보다|대비|와\s*비교하면|에\s*비해|와\s*비교해)\s*.{0,20}\d'
    r'|'
    r'\d[\d,\.]*\s*(?:배|%)\s*(?:더|이상|미만|높|낮|많|적|크|작|증가|감소)'
)

# 예측 주장
_PREDICTION_PATTERN = re.compile(
    r'(?:할\s*것이다|될\s*것이다|할\s*전망|될\s*전망|할\s*예정|될\s*예정'
    r'|로\s*예상|것으로\s*(?:보인다|예상|전망|관측|분석)'
    r'|할\s*것으로|될\s*것으로)'
)

# ── 출처 감지 패턴 ──

# "~에 따르면", "~연구에 의하면"
_SOURCE_PHRASE_PATTERN = re.compile(
    r'(?:[\w가-힣]+(?:에\s*따르면|에\s*의하면|의\s*(?:연구|조사|보고서|발표|분석)에\s*(?:따르면|의하면)))'
)
# URL
_URL_PATTERN = re.compile(
    r'https?://[^\s\)\]\"\'<>]+'
)
# "출처:", "참고:", "Reference"
_SOURCE_KEYWORD_PATTERN = re.compile(
    r'(?:출처|참고|참조|Reference|Source|Ref)\s*[:：]',
    re.IGNORECASE,
)
# 연도 괄호 참조 (2020)~(2030)
_YEAR_REF_PATTERN = re.compile(
    r'\((?:19|20)\d{2}\)'
)


def _split_sentences(content: str) -> List[str]:
    """콘텐츠를 문장 단위로 분리합니다."""
    # 마크다운 헤더, 리스트 마커 제거
    cleaned = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)
    cleaned = re.sub(r'^\s*[-*]\s+', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\s*\d+\.\s+', '', cleaned, flags=re.MULTILINE)

    # 문장 분리: 마침표/물음표/느낌표/줄바꿈 기준
    sentences = re.split(r'(?<=[.。!?!？\n])\s*', cleaned)
    # 빈 문장 제거, 최소 길이 필터
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) >= 5]


def _detect_claim_type(sentence: str) -> Optional[str]:
    """문장에서 주장 유형을 감지합니다. 우선순위: quote > statistic > comparison > prediction > fact"""
    # 인용 감지 (최우선)
    if _QUOTE_PATTERN.search(sentence) or _QUOTE_VERB_PATTERN.search(sentence):
        return "quote"

    # 비교 주장 (통계보다 우선: "보다 N배" 등은 비교가 더 정확한 분류)
    if _COMPARISON_PATTERN.search(sentence):
        return "comparison"

    # 통계 주장
    if _STAT_UNIT_PATTERN.search(sentence) or _STAT_PHRASE_PATTERN.search(sentence):
        return "statistic"

    # 예측 주장
    if _PREDICTION_PATTERN.search(sentence):
        return "prediction"

    # 사실 주장 (가장 넓은 범위이므로 마지막)
    if _ABSOLUTE_EXPRESSIONS.search(sentence):
        return "fact"
    if _HISTORICAL_PATTERN.search(sentence):
        return "fact"

    return None


def _detect_source(sentence: str, full_content: str) -> tuple[bool, Optional[str]]:
    """문장 및 전체 콘텐츠에서 출처 존재 여부를 감지합니다.

    Returns:
        (has_source, source_text)
    """
    # 문장 내 출처 패턴
    match = _SOURCE_PHRASE_PATTERN.search(sentence)
    if match:
        return True, match.group(0)

    # 문장 내 URL
    url_match = _URL_PATTERN.search(sentence)
    if url_match:
        return True, url_match.group(0)

    # 문장 내 연도 참조
    year_match = _YEAR_REF_PATTERN.search(sentence)
    if year_match:
        return True, year_match.group(0)

    # 문장 내 출처 키워드
    kw_match = _SOURCE_KEYWORD_PATTERN.search(sentence)
    if kw_match:
        return True, kw_match.group(0)

    return False, None


def _determine_severity(claim_type: str, sentence: str) -> str:
    """주장 유형과 내용에 따라 출처 미비 시 심각도를 결정합니다."""
    if claim_type == "statistic":
        return "high"

    if claim_type == "quote":
        return "high"

    if claim_type == "fact":
        if _ABSOLUTE_EXPRESSIONS.search(sentence):
            return "high"
        return "medium"

    if claim_type == "comparison":
        return "medium"

    if claim_type == "prediction":
        return "low"

    return "low"


def _generate_suggestions(claims: List[Dict]) -> List[str]:
    """미인용 주장 기반 개선 제안을 생성합니다."""
    suggestions = []
    uncited = [c for c in claims if c["needs_citation"]]

    if not uncited:
        return ["모든 주장에 출처가 포함되어 있습니다. 우수한 인용 품질입니다."]

    # 유형별 미인용 수 집계
    type_counts: Dict[str, int] = {}
    for c in uncited:
        type_counts[c["type"]] = type_counts.get(c["type"], 0) + 1

    type_labels = {
        "statistic": "통계 수치",
        "fact": "사실 주장",
        "quote": "인용문",
        "comparison": "비교 주장",
        "prediction": "예측",
    }

    for ctype, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        label = type_labels.get(ctype, ctype)
        suggestions.append(f"출처가 없는 {label}이(가) {count}건 있습니다. 근거 자료를 추가하세요.")

    high_uncited = [c for c in uncited if c["severity"] == "high"]
    if high_uncited:
        suggestions.append(
            f"심각도 높음(high) 미인용 주장이 {len(high_uncited)}건 있습니다. "
            "우선적으로 출처를 보강하세요."
        )

    return suggestions


_EMPTY_RESULT = {
    "claims": [],
    "summary": {
        "total_claims": 0,
        "cited": 0,
        "uncited": 0,
        "citation_rate": 0.0,
    },
    "credibility_score": 100.0,
    "suggestions": [],
}


def _scan_claims(sentences: List[str], content: str) -> List[Dict]:
    """문장에서 주장을 감지하고 출처 여부를 분석합니다."""
    claims = []
    for sentence in sentences:
        claim_type = _detect_claim_type(sentence)
        if claim_type is None:
            continue
        has_source, source = _detect_source(sentence, content)
        claims.append({
            "text": sentence,
            "type": claim_type,
            "has_source": has_source,
            "source": source,
            "needs_citation": not has_source,
            "severity": _determine_severity(claim_type, sentence),
        })
    return claims


def _compute_credibility(claims: List[Dict]) -> tuple:
    """신뢰도 점수와 요약 통계를 계산합니다.

    Returns:
        (total, cited, uncited, citation_rate, credibility_score)
    """
    total = len(claims)
    cited = sum(1 for c in claims if c["has_source"])
    uncited = total - cited
    citation_rate = (cited / total * 100) if total > 0 else 0.0

    high_uncited = sum(1 for c in claims if c["severity"] == "high" and c["needs_citation"])
    uncited_high_ratio = (high_uncited / total) if total > 0 else 0.0
    credibility_score = max(0.0, min(100.0,
        citation_rate * 0.6 + (100 - uncited_high_ratio * 100) * 0.4))

    return total, cited, uncited, round(citation_rate, 2), round(credibility_score, 2)


def verify_claims(content: str) -> dict:
    """콘텐츠에서 주장을 감지하고 출처 필요 여부를 분석합니다.

    Args:
        content: 분석할 텍스트 콘텐츠 (마크다운 가능)

    Returns:
        claims, summary, credibility_score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)
    try:

        claims = _scan_claims(_split_sentences(content), content)
        total, cited, uncited, citation_rate, credibility_score = _compute_credibility(claims)

        return {
            "claims": claims,
            "summary": {
                "total_claims": total,
                "cited": cited,
                "uncited": uncited,
                "citation_rate": citation_rate,
            },
            "credibility_score": credibility_score,
            "suggestions": _generate_suggestions(claims),
        }
    except Exception as e:
        logger.error(f"주장 검증 처리 실패: {e}")
        return dict(_EMPTY_RESULT)
