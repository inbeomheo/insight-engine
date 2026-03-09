"""
SERP 브리프 + 리서치 브리프 서비스

키워드/주제 기반으로 SERP 분석 브리프와 리서치 브리프를 규칙 기반으로 생성합니다.
외부 API 호출 없이 순수 Python 로직만 사용합니다.
"""
import re
import hashlib
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── PAA 질문 템플릿 (카테고리별) ──

_PAA_TEMPLATES = {
    'definition': [
        '{keyword}(이)란 무엇인가요?',
        '{keyword}의 뜻과 의미는?',
        '{keyword}을(를) 쉽게 설명하면?',
    ],
    'how': [
        '{keyword} 하는 방법은?',
        '{keyword} 시작하려면 어떻게 해야 하나요?',
        '{keyword}을(를) 효과적으로 활용하는 법은?',
    ],
    'comparison': [
        '{keyword}의 장단점은 무엇인가요?',
        '{keyword} vs 대안 비교는?',
        '{keyword}을(를) 선택할 때 고려할 점은?',
    ],
    'best': [
        '{keyword} 추천 순위는?',
        '가장 좋은 {keyword}은(는)?',
        '{keyword} 인기 있는 것은?',
    ],
    'cost': [
        '{keyword} 비용은 얼마인가요?',
        '{keyword} 가격 비교는?',
        '{keyword} 무료로 사용할 수 있나요?',
    ],
}

# ── 난이도 분류 키워드 ──

_HIGH_DIFFICULTY_SIGNALS = [
    '보험', '대출', '부동산', '주식', '투자', '법률', '의료', '건강',
    '다이어트', '재테크', '취업', '이직', 'seo', '마케팅',
    'insurance', 'loan', 'mortgage', 'investment', 'legal', 'medical',
]

_LOW_DIFFICULTY_SIGNALS = [
    '후기', '리뷰', '일기', '일상', '취미', '레시피', '요리법',
    '감상', '소감', '여행기', '체험', '경험담',
    'review', 'diary', 'hobby', 'recipe',
]

# ── 콘텐츠 갭 템플릿 ──

_CONTENT_GAP_TEMPLATES = [
    '{keyword}의 실제 사례와 케이스 스터디',
    '{keyword} 관련 최신 트렌드와 변화',
    '{keyword} 초보자를 위한 단계별 가이드',
    '{keyword}의 숨겨진 리스크와 주의사항',
    '{keyword} 전문가 인터뷰 및 의견',
    '{keyword} 데이터 기반 분석',
    '{keyword} FAQ 및 자주 묻는 질문 정리',
    '{keyword} 비용 대비 효과 분석',
]

# ── 리서치 각도 템플릿 ──

_ANGLE_TEMPLATES = [
    '초보자 관점: {topic}을(를) 처음 접하는 사람을 위한 입문 가이드',
    '전문가 분석: {topic}의 심층 기술적 분석',
    '트렌드 관점: {topic}의 최근 동향과 미래 전망',
    '비교 관점: {topic}과(와) 유사 대안의 비교 분석',
    '실용 관점: {topic}의 실전 활용법과 팁',
    '비판적 관점: {topic}의 한계와 개선 방향',
]

# ── 핵심 질문 템플릿 ──

_KEY_QUESTION_TEMPLATES = [
    '{topic}의 핵심 개념은 무엇인가?',
    '{topic}이(가) 중요한 이유는?',
    '{topic}의 주요 구성 요소는?',
    '{topic}을(를) 실제로 적용하려면?',
    '{topic}의 성공/실패 사례는?',
    '{topic} 관련 흔한 오해는?',
    '{topic}의 최신 동향은?',
    '{topic}과(와) 관련된 주요 논쟁은?',
]

# ── 증거 갭 템플릿 ──

_EVIDENCE_GAP_TEMPLATES = [
    '{topic}에 대한 정량적 데이터 (통계, 수치)',
    '{topic} 관련 학술 연구 및 논문',
    '{topic} 실무 전문가의 1차 증언',
    '{topic}의 장기적 효과에 대한 추적 데이터',
    '{topic} 국내외 비교 데이터',
]

# ── 소스 유형 ──

_SOURCE_TYPES = [
    '학술 논문 및 연구 보고서',
    '업계 전문 미디어 및 뉴스',
    '공식 통계 및 정부 자료',
    '전문가 인터뷰 및 팟캐스트',
    '사용자 후기 및 커뮤니티 토론',
    '기업 공식 발표 및 백서',
]

# ── 대상 독자 분류 ──

_AUDIENCE_KEYWORDS = {
    '개발': '소프트웨어 개발자 및 IT 전문가',
    '프로그래밍': '소프트웨어 개발자 및 IT 전문가',
    '코딩': '소프트웨어 개발자 및 IT 전문가',
    '마케팅': '마케터 및 비즈니스 담당자',
    '광고': '마케터 및 비즈니스 담당자',
    '투자': '개인 투자자 및 재무 관심자',
    '주식': '개인 투자자 및 재무 관심자',
    '요리': '요리에 관심 있는 일반인',
    '레시피': '요리에 관심 있는 일반인',
    '건강': '건강 관리에 관심 있는 일반인',
    '운동': '피트니스 및 건강 관심자',
    '여행': '여행 계획 중인 일반인',
    '교육': '학생, 교육자 및 학부모',
    '육아': '부모 및 예비 부모',
    '디자인': '디자이너 및 크리에이터',
    'ai': 'AI/ML 관심 기술 전문가 및 일반인',
    '인공지능': 'AI/ML 관심 기술 전문가 및 일반인',
}


@dataclass
class SerpBrief:
    """SERP 분석 브리프 결과"""
    keyword: str
    paa_questions: list = field(default_factory=list)       # People Also Ask 질문
    competitor_pages: list = field(default_factory=list)     # 경쟁 페이지 정보
    recommended_length: int = 0                              # 권장 글 길이 (단어 수)
    content_gaps: list = field(default_factory=list)         # 콘텐츠 갭
    difficulty: str = 'medium'                               # 난이도


@dataclass
class ResearchBrief:
    """리서치 브리프 결과"""
    topic: str
    angles: list = field(default_factory=list)               # 다룰 수 있는 각도
    target_audience: str = ''                                # 대상 독자
    key_questions: list = field(default_factory=list)        # 핵심 질문
    evidence_gaps: list = field(default_factory=list)        # 증거 부족 영역
    recommended_sources: list = field(default_factory=list)  # 참고할 소스 유형


def _deterministic_seed(text: str) -> int:
    """텍스트에서 결정적 시드 값을 생성합니다 (동일 입력 → 동일 결과)."""
    return int(hashlib.md5(text.encode('utf-8')).hexdigest(), 16)


def _select_items(items: list, seed: int, count: int) -> list:
    """시드 기반으로 리스트에서 count개 항목을 결정적으로 선택합니다."""
    if len(items) <= count:
        return list(items)
    # 시드 기반 인덱스 셔플 (Fisher-Yates 변형)
    indices = list(range(len(items)))
    local_seed = seed
    for i in range(len(indices) - 1, 0, -1):
        local_seed = (local_seed * 1103515245 + 12345) & 0x7FFFFFFF
        j = local_seed % (i + 1)
        indices[i], indices[j] = indices[j], indices[i]
    selected_indices = sorted(indices[:count])
    return [items[i] for i in selected_indices]


def _classify_difficulty(keyword: str) -> str:
    """키워드의 경쟁 난이도를 분류합니다.

    Returns:
        'easy', 'medium', 'hard' 중 하나
    """
    kw_lower = keyword.lower().strip()

    # 고난이도 시그널
    for signal in _HIGH_DIFFICULTY_SIGNALS:
        if signal in kw_lower:
            return 'hard'

    # 저난이도 시그널
    for signal in _LOW_DIFFICULTY_SIGNALS:
        if signal in kw_lower:
            return 'easy'

    # 키워드 길이 기반 추정 (긴 키워드 = 롱테일 = 쉬움)
    word_count = len(kw_lower.split())
    if word_count >= 4:
        return 'easy'
    elif word_count == 1:
        return 'hard'

    return 'medium'


def _generate_paa_questions(keyword: str) -> list:
    """키워드에 대한 PAA(People Also Ask) 질문을 생성합니다.

    최소 3개 이상의 질문을 반환합니다.
    """
    seed = _deterministic_seed(keyword)
    questions = []

    # 각 카테고리에서 질문 선택
    categories = list(_PAA_TEMPLATES.keys())
    selected_cats = _select_items(categories, seed, 3)

    for cat in selected_cats:
        templates = _PAA_TEMPLATES[cat]
        # 카테고리별 첫 번째 템플릿 사용
        q = templates[0].format(keyword=keyword)
        questions.append(q)

    # 최소 3개 보장: 부족하면 다른 카테고리에서 추가
    remaining_cats = [c for c in categories if c not in selected_cats]
    idx = 0
    while len(questions) < 3 and idx < len(remaining_cats):
        cat = remaining_cats[idx]
        q = _PAA_TEMPLATES[cat][0].format(keyword=keyword)
        questions.append(q)
        idx += 1

    return questions


def _generate_competitor_pages(keyword: str, difficulty: str) -> list:
    """가상의 경쟁 페이지 정보를 규칙 기반으로 생성합니다."""
    seed = _deterministic_seed(keyword)

    # 난이도별 경쟁 페이지 수
    page_counts = {'easy': 3, 'medium': 5, 'hard': 7}
    count = page_counts.get(difficulty, 5)

    # 경쟁 사이트 도메인 풀
    domains = [
        'blog.example.com', 'wiki.example.org', 'guide.example.net',
        'howto.example.com', 'tips.example.io', 'review.example.com',
        'learn.example.org', 'info.example.net', 'expert.example.com',
    ]

    # 글 길이 범위 (난이도별)
    length_ranges = {
        'easy': (800, 1500),
        'medium': (1500, 3000),
        'hard': (2500, 5000),
    }
    min_len, max_len = length_ranges.get(difficulty, (1500, 3000))

    pages = []
    selected_domains = _select_items(domains, seed, count)

    for i, domain in enumerate(selected_domains):
        # 결정적 단어 수 생성
        page_seed = (seed + i * 7919) & 0x7FFFFFFF
        word_count = min_len + (page_seed % (max_len - min_len + 1))
        pages.append({
            'url': f'https://{domain}/{keyword.replace(" ", "-").lower()}',
            'title': f'{keyword} - 완벽 가이드 #{i + 1}',
            'word_count': word_count,
        })

    return pages


def _calculate_recommended_length(competitor_pages: list, difficulty: str) -> int:
    """경쟁 페이지 분석을 기반으로 권장 글 길이를 계산합니다."""
    if not competitor_pages:
        return 1500

    # 경쟁 페이지 평균 길이의 1.2배
    avg_length = sum(p['word_count'] for p in competitor_pages) / len(competitor_pages)
    recommended = int(avg_length * 1.2)

    # 최소/최대 제한
    recommended = max(800, min(recommended, 6000))

    return recommended


def _generate_content_gaps(keyword: str) -> list:
    """경쟁 페이지에 없을 가능성이 높은 콘텐츠 갭을 생성합니다."""
    seed = _deterministic_seed(keyword)
    all_gaps = [t.format(keyword=keyword) for t in _CONTENT_GAP_TEMPLATES]
    return _select_items(all_gaps, seed, 4)


def generate_serp_brief(keyword: str) -> SerpBrief:
    """키워드에 대한 SERP 분석 브리프를 생성합니다.

    규칙 기반으로 PAA 질문, 경쟁 페이지, 권장 길이, 콘텐츠 갭, 난이도를 분석합니다.
    외부 API 호출 없이 동작합니다.

    Args:
        keyword: 분석할 키워드

    Returns:
        SerpBrief 데이터클래스

    Raises:
        ValueError: 키워드가 비어있을 때
    """
    if not keyword or not keyword.strip():
        raise ValueError('키워드가 비어있습니다.')

    keyword = keyword.strip()
    logger.info(f'SERP 브리프 생성 시작: {keyword}')

    difficulty = _classify_difficulty(keyword)
    paa_questions = _generate_paa_questions(keyword)
    competitor_pages = _generate_competitor_pages(keyword, difficulty)
    recommended_length = _calculate_recommended_length(competitor_pages, difficulty)
    content_gaps = _generate_content_gaps(keyword)

    brief = SerpBrief(
        keyword=keyword,
        paa_questions=paa_questions,
        competitor_pages=competitor_pages,
        recommended_length=recommended_length,
        content_gaps=content_gaps,
        difficulty=difficulty,
    )

    logger.info(f'SERP 브리프 생성 완료: difficulty={difficulty}, paa={len(paa_questions)}개')
    return brief


def _determine_target_audience(topic: str) -> str:
    """주제에 따른 대상 독자를 결정합니다."""
    topic_lower = topic.lower()
    for kw, audience in _AUDIENCE_KEYWORDS.items():
        if kw in topic_lower:
            return audience
    return '해당 주제에 관심 있는 일반 독자'


def _generate_angles(topic: str) -> list:
    """주제에 대해 다룰 수 있는 각도를 생성합니다. 최소 3개."""
    seed = _deterministic_seed(topic)
    all_angles = [t.format(topic=topic) for t in _ANGLE_TEMPLATES]
    # 최소 3개, 최대 5개
    count = min(5, max(3, len(all_angles)))
    return _select_items(all_angles, seed, count)


def _generate_key_questions(topic: str) -> list:
    """주제에 대한 핵심 질문을 생성합니다. 최소 5개."""
    seed = _deterministic_seed(topic)
    all_questions = [t.format(topic=topic) for t in _KEY_QUESTION_TEMPLATES]
    # 최소 5개 보장
    count = max(5, min(len(all_questions), 7))
    return _select_items(all_questions, seed, count)


def _generate_evidence_gaps(topic: str) -> list:
    """증거 부족 영역을 생성합니다."""
    seed = _deterministic_seed(topic)
    all_gaps = [t.format(topic=topic) for t in _EVIDENCE_GAP_TEMPLATES]
    return _select_items(all_gaps, seed, 3)


def _generate_recommended_sources(topic: str) -> list:
    """참고할 소스 유형을 생성합니다."""
    seed = _deterministic_seed(topic)
    return _select_items(list(_SOURCE_TYPES), seed, 4)


def generate_research_brief(topic: str, context: str = "") -> ResearchBrief:
    """주제에 대한 리서치 브리프를 생성합니다.

    규칙 기반으로 각도, 대상 독자, 핵심 질문, 증거 갭, 참고 소스를 분석합니다.
    외부 API 호출 없이 동작합니다.

    Args:
        topic: 리서치 주제
        context: 추가 맥락 (선택사항, 대상 독자 판별에 활용)

    Returns:
        ResearchBrief 데이터클래스

    Raises:
        ValueError: 주제가 비어있을 때
    """
    if not topic or not topic.strip():
        raise ValueError('주제가 비어있습니다.')

    topic = topic.strip()
    logger.info(f'리서치 브리프 생성 시작: {topic}')

    # context가 있으면 대상 독자 판별에 함께 사용
    audience_input = f'{topic} {context}'.strip() if context else topic
    target_audience = _determine_target_audience(audience_input)

    angles = _generate_angles(topic)
    key_questions = _generate_key_questions(topic)
    evidence_gaps = _generate_evidence_gaps(topic)
    recommended_sources = _generate_recommended_sources(topic)

    brief = ResearchBrief(
        topic=topic,
        angles=angles,
        target_audience=target_audience,
        key_questions=key_questions,
        evidence_gaps=evidence_gaps,
        recommended_sources=recommended_sources,
    )

    logger.info(f'리서치 브리프 생성 완료: angles={len(angles)}개, questions={len(key_questions)}개')
    return brief
