"""프롬프트 점유율 추적 서비스

프롬프트 목록에서 특정 브랜드 및 경쟁사의 언급 빈도를 분석하여
점유율(Share of Voice)을 계산합니다.
"""
import re
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class ShareReport:
    """브랜드 프롬프트 점유율 보고서"""
    brand: str                                  # 분석 대상 브랜드명
    total_prompts: int                          # 분석된 총 프롬프트 수
    brand_mentions: int                         # 브랜드 언급 횟수
    share_percent: float                        # 브랜드 점유율 (0~100)
    competitor_shares: dict[str, float]          # {경쟁사: 점유율}
    trending_prompts: list[str] = field(default_factory=list)  # 브랜드 언급된 프롬프트 목록


def _count_mentions(prompts: list[str], keyword: str) -> int:
    """프롬프트 목록에서 키워드 언급 횟수를 대소문자 무시하여 센다.

    단어 경계를 사용하여 부분 일치를 방지한다.
    예: "app" 검색 시 "apple"은 매칭하지 않음.

    Args:
        prompts: 프롬프트 문자열 리스트
        keyword: 검색할 키워드

    Returns:
        키워드가 언급된 프롬프트 수
    """
    if not keyword or not keyword.strip():
        return 0

    # 특수문자 이스케이프 후 경계 패턴 생성
    # \b는 단어문자(알파벳/숫자/_) 경계에만 작동하므로,
    # 키워드 시작/끝이 비단어문자(+, # 등)면 lookaround로 대체
    kw = keyword.strip()
    escaped = re.escape(kw)

    # 키워드 시작이 단어문자이면 \b, 아니면 (?<!\S) 또는 (?:^|(?<=\s))
    left = r'\b' if re.match(r'\w', kw) else r'(?:(?<=\s)|(?<=^)|(?:^))'
    # 키워드 끝이 단어문자이면 \b, 아니면 (?=\s|$)
    right = r'\b' if re.match(r'\w', kw[-1]) else r'(?=\s|$)'
    pattern = re.compile(rf'(?i){left}{escaped}{right}')
    count = 0
    for prompt in prompts:
        if pattern.search(prompt):
            count += 1
    return count


def _find_matching_prompts(prompts: list[str], keyword: str) -> list[str]:
    """키워드가 언급된 프롬프트들을 반환한다.

    Args:
        prompts: 프롬프트 문자열 리스트
        keyword: 검색할 키워드

    Returns:
        키워드가 포함된 프롬프트 리스트
    """
    if not keyword or not keyword.strip():
        return []

    kw = keyword.strip()
    escaped = re.escape(kw)
    left = r'\b' if re.match(r'\w', kw) else r'(?:(?<=\s)|(?<=^)|(?:^))'
    right = r'\b' if re.match(r'\w', kw[-1]) else r'(?=\s|$)'
    pattern = re.compile(rf'(?i){left}{escaped}{right}')
    return [p for p in prompts if pattern.search(p)]


def _calculate_share(mentions: int, total: int) -> float:
    """점유율을 백분율로 계산한다. (소수점 둘째 자리 반올림)

    Args:
        mentions: 언급 횟수
        total: 전체 프롬프트 수

    Returns:
        0.0 ~ 100.0 사이 백분율
    """
    if total <= 0:
        return 0.0
    return round((mentions / total) * 100, 2)


def track_prompt_share(
    prompts: list[str],
    brand: str,
    competitors: list[str] | None = None,
) -> ShareReport:
    """프롬프트 목록에서 브랜드/경쟁사 언급 점유율을 계산한다.

    Args:
        prompts: 분석할 프롬프트 문자열 리스트
        brand: 점유율을 추적할 브랜드명
        competitors: 비교할 경쟁사 이름 리스트 (선택)

    Returns:
        ShareReport 데이터클래스

    Raises:
        ValueError: brand가 빈 문자열이거나 prompts가 None인 경우
    """
    if prompts is None:
        raise ValueError("prompts는 None일 수 없습니다")
    if not brand or not brand.strip():
        raise ValueError("brand는 빈 문자열일 수 없습니다")

    competitors = competitors or []
    total = len(prompts)

    # 브랜드 언급 수 및 점유율 계산
    brand_mentions = _count_mentions(prompts, brand)
    brand_share = _calculate_share(brand_mentions, total)

    # 경쟁사별 점유율 계산
    competitor_shares: dict[str, float] = {}
    for comp in competitors:
        comp_stripped = comp.strip()
        if not comp_stripped:
            continue
        comp_mentions = _count_mentions(prompts, comp_stripped)
        competitor_shares[comp_stripped] = _calculate_share(comp_mentions, total)

    # 브랜드가 언급된 프롬프트 수집 (트렌딩)
    trending = _find_matching_prompts(prompts, brand)

    return ShareReport(
        brand=brand.strip(),
        total_prompts=total,
        brand_mentions=brand_mentions,
        share_percent=brand_share,
        competitor_shares=competitor_shares,
        trending_prompts=trending,
    )


def compare_brands(
    prompts: list[str],
    brands: list[str],
) -> dict[str, float]:
    """여러 브랜드의 점유율을 한번에 비교한다.

    Args:
        prompts: 분석할 프롬프트 리스트
        brands: 비교할 브랜드명 리스트

    Returns:
        {브랜드명: 점유율} 딕셔너리 (점유율 내림차순 정렬)
    """
    if not prompts or not brands:
        return {}

    total = len(prompts)
    shares: dict[str, float] = {}
    for b in brands:
        b_stripped = b.strip()
        if not b_stripped:
            continue
        mentions = _count_mentions(prompts, b_stripped)
        shares[b_stripped] = _calculate_share(mentions, total)

    # 점유율 내림차순 정렬
    return dict(sorted(shares.items(), key=lambda x: x[1], reverse=True))


def get_top_mentioned_terms(
    prompts: list[str],
    terms: list[str],
    top_n: int = 5,
) -> list[tuple[str, int]]:
    """주어진 용어 목록에서 가장 많이 언급된 상위 N개를 반환한다.

    Args:
        prompts: 분석할 프롬프트 리스트
        terms: 검색할 용어 리스트
        top_n: 반환할 상위 개수

    Returns:
        [(용어, 언급횟수), ...] 리스트 (내림차순)
    """
    if not prompts or not terms:
        return []

    counter = Counter()
    for term in terms:
        term_stripped = term.strip()
        if not term_stripped:
            continue
        counter[term_stripped] = _count_mentions(prompts, term_stripped)

    return counter.most_common(top_n)
