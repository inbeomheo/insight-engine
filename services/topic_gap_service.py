"""
토픽 갭 분석 서비스

현재 콘텐츠와 경쟁/참고 콘텐츠를 비교하여
빠진 하위 주제, 질문, 키워드를 찾아 보강 우선순위를 제안합니다.
AI API 호출 없이 규칙 기반으로 동작합니다.
"""
import re
import logging
from collections import Counter
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# 한국어 조사 패턴 (단어 끝에서 제거)
_JOSA_PATTERN = re.compile(
    r'(은|는|이|가|을|를|의|에|와|과|도|로|으로|에서|까지|부터|처럼|만큼|라고|이라|한테|에게|께서)$'
)

# 불용어 (분석에서 제외)
_STOPWORDS = {
    # 한국어 기능어
    '그', '이', '저', '것', '수', '등', '및', '더', '또', '를', '을', '에', '의', '가',
    '은', '는', '로', '와', '과', '도', '한', '할', '하는', '하고', '해서', '있는',
    '없는', '되는', '되고', '합니다', '있습니다', '없습니다', '됩니다', '입니다',
    '그리고', '하지만', '그러나', '따라서', '때문에', '그래서', '또한', '이런',
    '저런', '그런', '어떤', '모든', '각각', '매우', '아주', '정말', '많은',
    '위해', '대한', '통해', '하여', '있다', '없다', '된다', '한다', '이다',
    # 영어 기능어
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'and', 'or', 'but', 'in',
    'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'it', 'this',
    'that', 'not', 'no', 'so', 'if', 'as', 'its', 'they', 'them', 'their',
    'then', 'than', 'when', 'what', 'which', 'who', 'how', 'all', 'each',
    'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'only',
    'own', 'same', 'very', 'just', 'about', 'also', 'into', 'over', 'after',
}

# 구조적 갭 탐지 패턴
_HEADING_PATTERN = re.compile(r'(^|\n)(#{1,6}\s|[A-Z가-힣].{2,30}\n[-=]{3,})')
_EXAMPLE_PATTERN = re.compile(r'(예[를시]|예를\s*들[어면]|example|e\.g\.|for\s+instance)', re.IGNORECASE)
_DEFINITION_PATTERN = re.compile(r'(이란|이?란\s*(무엇|뭐)|정의|개념|means?|definition|refers?\s+to)', re.IGNORECASE)
_CONCLUSION_PATTERN = re.compile(r'(결론|마무리|요약하[면자]|정리하[면자]|conclusion|summary|in\s+conclusion)', re.IGNORECASE)
_QUESTION_PATTERN = re.compile(r'[^.!]\?')

# 일반적 질문 패턴 제안 템플릿
_GENERAL_QUESTION_TEMPLATES = [
    '{topic}이란 무엇인가?',
    '{topic}의 장단점은?',
    '{topic} 사용 방법은?',
    '{topic}의 주요 특징은?',
    '{topic} 시작하는 방법은?',
]


def _remove_josa(word: str) -> str:
    """한국어 조사를 제거합니다."""
    return _JOSA_PATTERN.sub('', word)


def _extract_topics(text: str, min_count: int = 2) -> Counter:
    """텍스트에서 토픽(명사/단어)을 추출합니다.

    한국어 명사(2-8자), 영어 단어(3자+)를 추출하고
    2회 이상 등장하는 것만 반환합니다.
    """
    if not text:
        return Counter()

    # 한국어 단어 추출 (2-8자)
    ko_words = re.findall(r'[가-힣]{2,8}', text)
    # 조사 제거 후 필터링
    ko_cleaned = []
    for w in ko_words:
        cleaned = _remove_josa(w)
        if len(cleaned) >= 2 and cleaned not in _STOPWORDS:
            ko_cleaned.append(cleaned)

    # 영어 단어 추출 (3자+)
    en_words = re.findall(r'[a-zA-Z]{3,}', text)
    en_cleaned = [w.lower() for w in en_words if w.lower() not in _STOPWORDS]

    counts = Counter(ko_cleaned + en_cleaned)

    # min_count 이상 등장한 토픽만 필터링
    return Counter({word: count for word, count in counts.items() if count >= min_count})


def _extract_questions(text: str) -> List[str]:
    """텍스트에서 질문 문장을 추출합니다."""
    if not text:
        return []

    # 문장 분리
    sentences = re.split(r'[.!?\n]+', text)
    questions = []
    for s in sentences:
        s = s.strip()
        # 원본 텍스트에서 ? 로 끝나는 문장 찾기
        if s and '?' in text[text.find(s):text.find(s) + len(s) + 2] if s in text else False:
            questions.append(s.strip() + '?')

    # 좀 더 안정적인 방식: ? 포함 문장 직접 추출
    question_sentences = []
    for match in re.finditer(r'([^.!?\n][^.!?\n]*\?)', text):
        q = match.group(1).strip()
        if len(q) > 3:  # 너무 짧은 것 제외
            question_sentences.append(q)

    return list(dict.fromkeys(question_sentences))  # 중복 제거, 순서 유지


def _calculate_structural_score(text: str) -> float:
    """콘텐츠 구조적 완성도를 0-100 점수로 계산합니다."""
    if not text or len(text.strip()) < 10:
        return 0.0

    score = 0.0
    checks = 0
    total = 5

    # 1. 헤딩 존재 여부
    if _HEADING_PATTERN.search(text):
        score += 20
        checks += 1

    # 2. 예시 존재 여부
    if _EXAMPLE_PATTERN.search(text):
        score += 20
        checks += 1

    # 3. 정의/개념 설명 존재 여부
    if _DEFINITION_PATTERN.search(text):
        score += 20
        checks += 1

    # 4. 결론/요약 존재 여부
    if _CONCLUSION_PATTERN.search(text):
        score += 20
        checks += 1

    # 5. 충분한 길이 (500자 이상)
    if len(text.strip()) >= 500:
        score += 20
        checks += 1

    return score


def _detect_structural_gaps(text: str) -> List[Dict[str, Any]]:
    """구조적 갭을 탐지합니다 (reference 없을 때 사용)."""
    gaps = []

    if not _HEADING_PATTERN.search(text):
        gaps.append({
            'topic': '섹션 구분 (헤딩)',
            'importance': 'high',
            'found_in': [],
            'suggestion': '콘텐츠에 명확한 섹션 구분(헤딩)을 추가하면 가독성이 향상됩니다.',
        })

    if not _EXAMPLE_PATTERN.search(text):
        gaps.append({
            'topic': '구체적 예시',
            'importance': 'medium',
            'found_in': [],
            'suggestion': '구체적인 예시나 사례를 추가하면 이해도가 높아집니다.',
        })

    if not _DEFINITION_PATTERN.search(text):
        gaps.append({
            'topic': '용어 정의',
            'importance': 'medium',
            'found_in': [],
            'suggestion': '핵심 용어에 대한 정의나 개념 설명을 추가해보세요.',
        })

    if not _CONCLUSION_PATTERN.search(text):
        gaps.append({
            'topic': '결론/요약',
            'importance': 'low',
            'found_in': [],
            'suggestion': '결론이나 요약 섹션을 추가하면 콘텐츠가 완성도 있어 보입니다.',
        })

    if not _QUESTION_PATTERN.search(text):
        gaps.append({
            'topic': '질문/FAQ',
            'importance': 'low',
            'found_in': [],
            'suggestion': '독자가 궁금해할 만한 질문과 답변을 포함해보세요.',
        })

    return gaps


def _generate_general_questions(topics: Counter) -> List[str]:
    """주요 토픽 기반으로 일반적 질문을 생성합니다."""
    questions = []
    # 상위 3개 토픽으로 질문 생성
    top_topics = [word for word, _ in topics.most_common(3)]
    for topic in top_topics:
        for template in _GENERAL_QUESTION_TEMPLATES[:2]:  # 토픽당 2개
            questions.append(template.format(topic=topic))
    return questions


def analyze_topic_gaps(
    content: str,
    reference_contents: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """현재 콘텐츠와 참고 콘텐츠를 비교하여 토픽 갭을 분석합니다.

    Args:
        content: 내 콘텐츠 텍스트
        reference_contents: 참고 콘텐츠 리스트 [{"title": str, "content": str}, ...]

    Returns:
        {
            "gaps": list,             # 빠진 주제 목록
            "coverage_score": float,  # 0-100 주제 커버리지
            "my_unique_topics": list,  # 내 콘텐츠에만 있는 주제
            "common_topics": list,    # 공통 주제
            "missing_questions": list, # 빠진 질문
            "suggestions": list,      # 보강 제안
        }
    """
    # 빈 콘텐츠 처리
    if not content or not content.strip():
        return {
            'gaps': [],
            'coverage_score': 0.0,
            'my_unique_topics': [],
            'common_topics': [],
            'missing_questions': [],
            'suggestions': ['분석할 콘텐츠가 없습니다. 콘텐츠를 입력해주세요.'],
        }

    my_topics = _extract_topics(content)
    my_topic_set = set(my_topics.keys())

    # reference가 없는 경우: 자체 구조 분석
    if not reference_contents:
        structural_gaps = _detect_structural_gaps(content)
        coverage = _calculate_structural_score(content)
        missing_questions = _generate_general_questions(my_topics)

        suggestions = []
        if coverage < 60:
            suggestions.append('콘텐츠 구조를 보강해보세요 (헤딩, 예시, 정의, 결론).')
        if len(my_topics) < 5:
            suggestions.append('다루는 주제가 적습니다. 관련 하위 주제를 추가해보세요.')
        if not missing_questions:
            suggestions.append('독자 관점의 질문과 답변을 포함하면 도움이 됩니다.')

        return {
            'gaps': structural_gaps,
            'coverage_score': round(coverage, 1),
            'my_unique_topics': sorted(my_topic_set),
            'common_topics': [],
            'missing_questions': missing_questions[:5],
            'suggestions': suggestions if suggestions else ['구조적으로 잘 작성된 콘텐츠입니다.'],
        }

    # reference가 있는 경우: 비교 분석
    # 참고 콘텐츠별 토픽 추출
    ref_topics_by_source: Dict[str, set] = {}  # title -> set of topics
    ref_topic_counter = Counter()  # 전체 참고 콘텐츠 토픽 출현 횟수 (소스 수 기준)
    ref_questions: List[str] = []

    for ref in reference_contents:
        title = ref.get('title', '참고 콘텐츠')
        ref_text = ref.get('content', '')
        if not ref_text:
            continue

        topics = _extract_topics(ref_text)
        topic_set = set(topics.keys())
        ref_topics_by_source[title] = topic_set

        # 소스별 토픽 카운트 (몇 개 소스에서 등장했는지)
        for topic in topic_set:
            ref_topic_counter[topic] += 1

        # 질문 추출
        ref_questions.extend(_extract_questions(ref_text))

    all_ref_topics = set(ref_topic_counter.keys())

    # 갭: reference에 있지만 내 콘텐츠에 없는 토픽
    missing_topics = all_ref_topics - my_topic_set
    common_topics = my_topic_set & all_ref_topics
    unique_topics = my_topic_set - all_ref_topics

    # 갭 목록 생성 (importance 결정)
    gaps = []
    for topic in missing_topics:
        source_count = ref_topic_counter[topic]
        found_in = [
            title for title, topics in ref_topics_by_source.items()
            if topic in topics
        ]

        if source_count >= 2:
            importance = 'high'
        else:
            importance = 'medium'

        gaps.append({
            'topic': topic,
            'importance': importance,
            'found_in': found_in,
            'suggestion': f"'{topic}' 주제를 추가하면 콘텐츠 커버리지가 향상됩니다.",
        })

    # importance 순서대로 정렬 (high > medium > low)
    importance_order = {'high': 0, 'medium': 1, 'low': 2}
    gaps.sort(key=lambda g: (importance_order.get(g['importance'], 3), g['topic']))

    # coverage_score 계산: (공통 토픽 / 전체 reference 토픽) × 100
    if all_ref_topics:
        coverage = (len(common_topics) / len(all_ref_topics)) * 100
    else:
        coverage = 100.0  # 참고 토픽이 없으면 100

    # missing_questions: 참고에서 추출한 질문 중 내 콘텐츠에 답이 없는 것
    missing_questions = []
    for q in ref_questions:
        # 질문의 핵심 단어가 내 콘텐츠에 있는지 확인
        q_words = set(re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', q.lower()))
        q_words -= _STOPWORDS
        if q_words and not q_words.issubset(my_topic_set):
            missing_questions.append(q)

    missing_questions = list(dict.fromkeys(missing_questions))[:10]  # 중복 제거, 최대 10개

    # 제안 생성
    suggestions = []
    high_gaps = [g for g in gaps if g['importance'] == 'high']
    if high_gaps:
        topics_str = ', '.join(g['topic'] for g in high_gaps[:3])
        suggestions.append(f"우선적으로 다음 주제를 보강하세요: {topics_str}")
    if len(missing_topics) > len(common_topics):
        suggestions.append('참고 콘텐츠 대비 다루지 않은 주제가 많습니다. 콘텐츠 범위를 넓혀보세요.')
    if unique_topics:
        suggestions.append(f'차별화된 주제({len(unique_topics)}개)가 있어 독자에게 고유한 가치를 제공합니다.')
    if coverage < 50:
        suggestions.append('주제 커버리지가 50% 미만입니다. 핵심 토픽을 보강해보세요.')
    if not suggestions:
        suggestions.append('전반적으로 주제 커버리지가 양호합니다.')

    return {
        'gaps': gaps,
        'coverage_score': round(coverage, 1),
        'my_unique_topics': sorted(unique_topics),
        'common_topics': sorted(common_topics),
        'missing_questions': missing_questions,
        'suggestions': suggestions,
    }
