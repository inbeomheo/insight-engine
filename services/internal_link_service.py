"""
내부 링크 기회 탐지 서비스 (Internal Link Opportunity Finder)

여러 콘텐츠를 분석하여 내부 링크로 연결할 수 있는 기회를 찾고
앵커 텍스트를 추천합니다. AI API 호출 없이 순수 규칙 기반.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter

logger = logging.getLogger(__name__)

# 키워드 추출 시 최소/최대 글자수
_MIN_KEYWORD_LEN = 2
_MAX_KEYWORD_LEN = 8

# 키워드 최소 등장 횟수
_MIN_KEYWORD_FREQ = 2

# 앵커 텍스트 어절 범위
_MIN_ANCHOR_WORDS = 2
_MAX_ANCHOR_WORDS = 5

# 문맥 추출 시 전후 글자수
_CONTEXT_CHARS = 20

# 불용어 (관련성 없는 일반 단어)
_STOPWORDS = {
    '그리고', '하지만', '그래서', '따라서', '그러나', '또한', '이것',
    '저것', '여기', '거기', '우리', '이런', '저런', '그런', '어떤',
    '모든', '같은', '다른', '있는', '없는', '하는', '되는', '위한',
    '대한', '통해', '때문', '경우', '이상', '이하', '정도', '이후',
    '사이', '사용', '활용', '방법', '내용', '부분', '관련', '기반',
    'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are',
    'was', 'were', 'been', 'have', 'has', 'not', 'but', 'all',
}


def find_link_opportunities(contents: list, current_content: str = '') -> dict:
    """여러 콘텐츠를 분석하여 내부 링크 기회를 탐지합니다.

    Args:
        contents: 콘텐츠 목록.
            [{"id": str, "title": str, "content": str, "url": str(optional)}, ...]
        current_content: 현재 편집 중인 콘텐츠.
            이 콘텐츠에서 다른 콘텐츠로 링크할 기회를 찾음.
            빈 문자열이면 contents 간 모든 쌍의 기회를 양방향 분석.

    Returns:
        {
            "opportunities": [...],  # 링크 기회 목록
            "summary": {...},        # 요약 통계
            "orphan_contents": [...], # 고립 콘텐츠 ID
            "suggestions": [...],    # 개선 제안 목록
        }
    """
    # 빈 리스트 또는 1개 이하 → 기회 없음
    if not contents or len(contents) < 2:
        return _empty_result(contents)

    # 각 콘텐츠에서 핵심 키워드 추출
    content_keywords: Dict[str, Set[str]] = {}
    content_keyword_counts: Dict[str, Counter] = {}
    content_map: Dict[str, Dict] = {}

    for item in contents:
        cid = item.get('id', '')
        if not cid:
            continue
        content_map[cid] = item
        text = item.get('content', '')
        keywords, counts = _extract_keywords(text)
        content_keywords[cid] = keywords
        content_keyword_counts[cid] = counts

    if len(content_map) < 2:
        return _empty_result(contents)

    opportunities = []
    linked_ids: Set[str] = set()

    if current_content:
        # current_content 기준으로 다른 콘텐츠로의 링크 기회 탐지
        current_kw, current_counts = _extract_keywords(current_content)
        for cid, item in content_map.items():
            target_kw = content_keywords[cid]
            target_title = item.get('title', '')
            title_kw = _extract_title_keywords(target_title)

            opps = _find_pairwise_opportunities(
                source_text=current_content,
                source_keywords=current_kw,
                target_id=cid,
                target_title=target_title,
                target_keywords=target_kw,
                title_keywords=title_kw,
                target_keyword_counts=content_keyword_counts[cid],
            )
            if opps:
                linked_ids.add(cid)
                opportunities.extend(opps)
    else:
        # contents 간 모든 쌍의 링크 기회 분석 (양방향)
        cids = list(content_map.keys())
        for i, src_id in enumerate(cids):
            src_item = content_map[src_id]
            src_text = src_item.get('content', '')
            src_kw = content_keywords[src_id]

            for j, tgt_id in enumerate(cids):
                if i == j:
                    continue
                tgt_item = content_map[tgt_id]
                tgt_title = tgt_item.get('title', '')
                tgt_kw = content_keywords[tgt_id]
                title_kw = _extract_title_keywords(tgt_title)

                opps = _find_pairwise_opportunities(
                    source_text=src_text,
                    source_keywords=src_kw,
                    target_id=tgt_id,
                    target_title=tgt_title,
                    target_keywords=tgt_kw,
                    title_keywords=title_kw,
                    target_keyword_counts=content_keyword_counts[tgt_id],
                )
                if opps:
                    linked_ids.add(src_id)
                    linked_ids.add(tgt_id)
                    opportunities.extend(opps)

    # 관련성 점수 내림차순 정렬
    opportunities.sort(key=lambda x: x['relevance_score'], reverse=True)

    # 고립 콘텐츠 탐지
    all_ids = set(content_map.keys())
    orphan_contents = sorted(all_ids - linked_ids)

    # 요약 통계
    high_relevance = sum(1 for o in opportunities if o['relevance_score'] >= 70)
    # 고유한 (source→target) 쌍 수
    linked_pairs = len(set(
        (o.get('_source_id', ''), o['target_id']) for o in opportunities
    ))

    # 제안 생성
    suggestions = _generate_suggestions(
        opportunities, orphan_contents, content_map
    )

    # 내부 키 제거
    for opp in opportunities:
        opp.pop('_source_id', None)

    return {
        'opportunities': opportunities,
        'summary': {
            'total_opportunities': len(opportunities),
            'high_relevance': high_relevance,
            'linked_pairs': linked_pairs,
        },
        'orphan_contents': orphan_contents,
        'suggestions': suggestions,
    }


# ============================================================
# 키워드 추출
# ============================================================

def _extract_keywords(text: str) -> Tuple[Set[str], Counter]:
    """텍스트에서 핵심 키워드를 추출합니다.

    2회 이상 등장하는 명사 2-8자를 키워드로 선정합니다.

    Returns:
        (키워드 집합, 키워드별 등장 횟수 Counter)
    """
    if not text:
        return set(), Counter()

    # 한글 및 영문 단어 추출
    words = re.findall(r'[가-힣a-zA-Z]+', text)
    # 길이 필터 + 소문자 정규화
    filtered = [
        w.lower() for w in words
        if _MIN_KEYWORD_LEN <= len(w) <= _MAX_KEYWORD_LEN
        and w.lower() not in _STOPWORDS
    ]

    counts = Counter(filtered)
    # 2회 이상 등장하는 것만 키워드로 선정
    keywords = {w for w, c in counts.items() if c >= _MIN_KEYWORD_FREQ}
    return keywords, counts


def _extract_title_keywords(title: str) -> Set[str]:
    """제목에서 키워드를 추출합니다 (빈도 제한 없음)."""
    if not title:
        return set()
    words = re.findall(r'[가-힣a-zA-Z]+', title)
    return {
        w.lower() for w in words
        if _MIN_KEYWORD_LEN <= len(w) <= _MAX_KEYWORD_LEN
        and w.lower() not in _STOPWORDS
    }


# ============================================================
# 쌍별 기회 탐지
# ============================================================

def _find_pairwise_opportunities(
    source_text: str,
    source_keywords: Set[str],
    target_id: str,
    target_title: str,
    target_keywords: Set[str],
    title_keywords: Set[str],
    target_keyword_counts: Counter,
    source_id: str = '',
) -> List[Dict[str, Any]]:
    """소스 텍스트에서 타겟 콘텐츠로의 링크 기회를 찾습니다."""
    if not target_keywords:
        return []

    # 소스 텍스트에 타겟 키워드가 등장하는지 확인
    common_keywords = source_keywords & target_keywords
    if not common_keywords:
        return []

    opportunities = []

    for keyword in common_keywords:
        # 소스 텍스트에서 키워드 위치 찾기
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        match = pattern.search(source_text)
        if not match:
            continue

        # 관련성 점수 계산
        score = _calculate_relevance(
            keyword=keyword,
            common_count=len(common_keywords),
            title_keywords=title_keywords,
            target_keyword_counts=target_keyword_counts,
            source_text=source_text,
            match_pos=match.start(),
        )

        # 앵커 텍스트 추천
        anchor = _suggest_anchor(source_text, match.start(), match.end(), keyword)

        # 문맥 추출
        context = _extract_context(source_text, match.start(), match.end())

        opportunities.append({
            'source_text': source_text[match.start():match.end()],
            'target_id': target_id,
            'target_title': target_title,
            'relevance_score': round(score, 1),
            'anchor_suggestion': anchor,
            'context': context,
            '_source_id': source_id,
        })

    # 같은 타겟에 대해 가장 관련성 높은 기회만 유지
    if opportunities:
        opportunities.sort(key=lambda x: x['relevance_score'], reverse=True)
        return [opportunities[0]]

    return []


# ============================================================
# 관련성 점수 계산
# ============================================================

def _calculate_relevance(
    keyword: str,
    common_count: int,
    title_keywords: Set[str],
    target_keyword_counts: Counter,
    source_text: str,
    match_pos: int,
) -> float:
    """관련성 점수를 계산합니다 (0-100).

    규칙:
    - 키워드 일치: 기본 30점
    - 제목 포함 시: +30 (총 50 → 기본 20 + 제목 보너스 30)
    - 공통 키워드 수: 2개 +20, 3개+ +30
    - 헤딩 근처 위치: +20
    """
    score = 0.0

    # 기본 키워드 일치 점수
    if keyword in title_keywords:
        # 제목에도 포함: 기본 20 + 보너스 30 = 50
        score += 50
    else:
        # 본문만 일치: 30
        score += 30

    # 공통 키워드 수 보너스
    if common_count >= 3:
        score += 30
    elif common_count >= 2:
        score += 20

    # 헤딩 근처 위치 보너스 (# 으로 시작하는 줄 근처)
    if _is_near_heading(source_text, match_pos):
        score += 20

    return min(score, 100.0)


def _is_near_heading(text: str, pos: int, radius: int = 100) -> bool:
    """주어진 위치가 마크다운 헤딩(#) 근처인지 확인합니다."""
    start = max(0, pos - radius)
    end = min(len(text), pos + radius)
    snippet = text[start:end]
    return bool(re.search(r'^#{1,6}\s', snippet, re.MULTILINE))


# ============================================================
# 앵커 텍스트 추천
# ============================================================

def _suggest_anchor(text: str, start: int, end: int, keyword: str) -> str:
    """매칭된 키워드를 포함하는 2-5어절 앵커 텍스트를 추천합니다.

    규칙:
    - 키워드가 1어절이면 주변 단어 포함하여 2-5어절로 확장
    - 6어절 이상이면 키워드 중심으로 축소
    """
    # 키워드 위치 주변의 넓은 범위 추출
    line_start = text.rfind('\n', 0, start)
    line_start = line_start + 1 if line_start != -1 else 0
    line_end = text.find('\n', end)
    line_end = line_end if line_end != -1 else len(text)

    line = text[line_start:line_end].strip()
    # 마크다운 헤딩 기호 제거
    line = re.sub(r'^#{1,6}\s*', '', line)

    if not line:
        return keyword

    # 어절 분리
    words = line.split()
    if not words:
        return keyword

    # 키워드가 포함된 어절 인덱스 찾기
    keyword_lower = keyword.lower()
    keyword_idx = -1
    for i, w in enumerate(words):
        # 어절에서 순수 텍스트만 추출하여 비교
        clean = re.sub(r'[^\w가-힣]', '', w).lower()
        if keyword_lower in clean:
            keyword_idx = i
            break

    if keyword_idx == -1:
        return keyword

    # 2-5어절 범위로 추출
    total_words = len(words)
    # 키워드 중심으로 양쪽 확장
    half = _MAX_ANCHOR_WORDS // 2
    anchor_start = max(0, keyword_idx - half)
    anchor_end = min(total_words, keyword_idx + half + 1)

    # 최소 어절 수 보장
    while anchor_end - anchor_start < _MIN_ANCHOR_WORDS and anchor_end < total_words:
        anchor_end += 1
    while anchor_end - anchor_start < _MIN_ANCHOR_WORDS and anchor_start > 0:
        anchor_start -= 1

    # 최대 어절 수 제한
    if anchor_end - anchor_start > _MAX_ANCHOR_WORDS:
        anchor_end = anchor_start + _MAX_ANCHOR_WORDS

    anchor_words = words[anchor_start:anchor_end]
    result = ' '.join(anchor_words)

    # 앞뒤 특수문자 제거
    result = result.strip('.,;:!?()[]{}"\' ')
    return result if result else keyword


# ============================================================
# 문맥 추출
# ============================================================

def _extract_context(text: str, start: int, end: int) -> str:
    """소스 텍스트에서 매칭 위치의 전후 20자 문맥을 추출합니다."""
    ctx_start = max(0, start - _CONTEXT_CHARS)
    ctx_end = min(len(text), end + _CONTEXT_CHARS)

    prefix = ('...' if ctx_start > 0 else '') + text[ctx_start:start]
    matched = text[start:end]
    suffix = text[end:ctx_end] + ('...' if ctx_end < len(text) else '')

    return f"{prefix}[{matched}]{suffix}"


# ============================================================
# 제안 생성
# ============================================================

def _generate_suggestions(
    opportunities: List[Dict],
    orphan_contents: List[str],
    content_map: Dict[str, Dict],
) -> List[str]:
    """분석 결과를 바탕으로 개선 제안을 생성합니다."""
    suggestions = []

    if orphan_contents:
        orphan_titles = [
            content_map[cid].get('title', cid) for cid in orphan_contents
            if cid in content_map
        ]
        if orphan_titles:
            suggestions.append(
                f"고립 콘텐츠 {len(orphan_titles)}개 발견: "
                f"'{', '.join(orphan_titles[:3])}' — "
                f"관련 키워드를 추가하면 링크 기회가 늘어납니다."
            )

    high_count = sum(1 for o in opportunities if o['relevance_score'] >= 70)
    if high_count > 0:
        suggestions.append(
            f"높은 관련성(70+) 기회 {high_count}개를 우선 적용하세요."
        )

    total = len(opportunities)
    if total == 0:
        suggestions.append(
            "콘텐츠 간 공통 키워드가 부족합니다. "
            "유사한 주제의 콘텐츠를 더 작성하면 링크 기회가 증가합니다."
        )
    elif total > 10:
        suggestions.append(
            f"링크 기회가 {total}개로 많습니다. "
            f"관련성 70점 이상 기회만 우선 적용하는 것을 권장합니다."
        )

    return suggestions


# ============================================================
# 빈 결과 헬퍼
# ============================================================

def _empty_result(contents: Optional[list] = None) -> dict:
    """기회가 없을 때의 빈 결과를 반환합니다."""
    orphans = []
    if contents:
        orphans = [c.get('id', '') for c in contents if c.get('id')]

    suggestions = []
    if not contents or len(contents) == 0:
        suggestions.append("분석할 콘텐츠가 없습니다.")
    elif len(contents) == 1:
        suggestions.append("콘텐츠가 1개뿐이므로 내부 링크 기회를 찾을 수 없습니다. 콘텐츠를 더 추가하세요.")

    return {
        'opportunities': [],
        'summary': {
            'total_opportunities': 0,
            'high_relevance': 0,
            'linked_pairs': 0,
        },
        'orphan_contents': orphans,
        'suggestions': suggestions,
    }
