"""
FAQ 자동 생성 서비스

콘텐츠에서 핵심 주제를 추출하여
자주 묻는 질문(FAQ)과 답변을 자동 생성합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 질문 생성 패턴
_QUESTION_PATTERNS = [
    # 정의형
    {'type': 'definition', 'template': '{topic}이란 무엇인가요?', 'answer_hint': '정의와 개념 설명'},
    # 방법형
    {'type': 'how_to', 'template': '{topic}은 어떻게 사용하나요?', 'answer_hint': '사용 방법과 절차'},
    # 이유형
    {'type': 'why', 'template': '{topic}이 왜 중요한가요?', 'answer_hint': '중요성과 이점'},
    # 비교형
    {'type': 'comparison', 'template': '{topic}의 장단점은 무엇인가요?', 'answer_hint': '장점과 단점 비교'},
    # 시작형
    {'type': 'getting_started', 'template': '{topic}을 시작하려면 어떻게 해야 하나요?', 'answer_hint': '시작 방법과 요구사항'},
    # 주의형
    {'type': 'caution', 'template': '{topic} 사용 시 주의할 점은?', 'answer_hint': '주의사항과 흔한 실수'},
]

# 토픽 추출 불용어
_STOPWORDS = {
    '있습니다', '합니다', '입니다', '됩니다', '것입니다', '위해', '통해',
    '대한', '하는', '이는', '있는', '되는', '않는', '경우', '방법',
    '사용', '필요', '가능', '다양', '제공', '포함', '진행', '설명',
}


_EMPTY_RESULT = {
    'faqs': [],
    'topics': [],
    'schema_json': '',
    'markdown': '',
    'suggestions': [],
}


def _build_faqs(topics: list, content: str, max_questions: int) -> list:
    """토픽 목록에서 FAQ 항목을 생성합니다."""
    sentences = [s.strip() for s in re.split(r'[.!?。]\s*|\n+', content) if len(s.strip()) >= 10]
    faqs = []

    for topic in topics[:max_questions]:
        related = [s for s in sentences if topic in s]
        if not related:
            related = sentences[:3]

        pattern = _select_pattern(topic, content, related)
        faqs.append({
            'question': pattern['template'].format(topic=topic),
            'answer': _generate_answer(topic, related, content),
            'type': pattern['type'],
            'topic': topic,
        })

    return faqs


def generate_faq(content: str, max_questions: int = 5) -> dict:
    """콘텐츠 기반 FAQ를 자동 생성합니다.

    Args:
        content: 분석할 콘텐츠
        max_questions: 최대 질문 수 (기본 5)

    Returns:
        faqs, topics, schema_json, markdown, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    topics = _extract_topics(content)
    if not topics:
        return {**_EMPTY_RESULT, 'suggestions': ['주제를 추출할 수 없습니다. 더 구체적인 콘텐츠가 필요합니다.']}

    faqs = _build_faqs(topics, content, max_questions)
    markdown = _build_faq_markdown(faqs)

    return {
        'faqs': faqs,
        'topics': topics,
        'schema_json': _build_faq_schema(faqs),
        'markdown': markdown,
        'word_count': len(markdown.split()),
        'suggestions': _generate_suggestions(faqs, topics),
    }


def _extract_topics(content: str) -> list:
    """콘텐츠에서 핵심 주제어를 추출합니다."""
    # 한국어 명사 (2~8자)
    words = re.findall(r'[가-힣]{2,8}', content)
    # 영어 단어 (2자+)
    eng_words = re.findall(r'[A-Za-z]{3,}', content)

    # 한국어 조사 제거 (은/는/이/가/을/를/의/에/와/과/도/로)
    _PARTICLES = re.compile(r'(은|는|이|가|을|를|의|에|와|과|도|로|으로|에서|까지|부터|만|라)$')

    freq = {}
    for w in words:
        stem = _PARTICLES.sub('', w)
        if len(stem) >= 2 and stem not in _STOPWORDS:
            freq[stem] = freq.get(stem, 0) + 1
    for w in eng_words:
        w_lower = w.lower()
        if len(w_lower) >= 3:
            freq[w] = freq.get(w, 0) + 1

    # 빈도 상위 + 최소 2회 이상
    sorted_topics = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    topics = [w for w, c in sorted_topics if c >= 2]

    return topics[:10]


def _select_pattern(topic: str, content: str, related: list) -> dict:
    """토픽에 가장 적합한 질문 패턴을 선택합니다."""
    content_lower = content.lower()

    # 방법/절차 언급이 있으면 how_to
    if any(k in content_lower for k in ['방법', '절차', '단계', '과정']):
        return _QUESTION_PATTERNS[1]  # how_to

    # 비교/차이 언급이 있으면 comparison
    if any(k in content for k in ['장점', '단점', '비교', '차이']):
        return _QUESTION_PATTERNS[3]  # comparison

    # 주의/유의 언급이 있으면 caution
    if any(k in content for k in ['주의', '유의', '실수', '위험']):
        return _QUESTION_PATTERNS[5]  # caution

    # 기본: 정의형
    return _QUESTION_PATTERNS[0]  # definition


def _generate_answer(topic: str, related: list, content: str) -> str:
    """관련 문장을 조합하여 답변을 생성합니다."""
    if not related:
        return f'{topic}에 대한 자세한 내용은 본문을 참조해 주세요.'

    # 가장 관련성 높은 문장 2~3개 조합
    selected = related[:3]
    answer = ' '.join(s.strip().rstrip('.!?。') for s in selected) + '.'

    # 너무 길면 자르기
    if len(answer) > 200:
        answer = answer[:197] + '...'

    return answer


def _build_faq_schema(faqs: list) -> str:
    """FAQ 구조화 데이터 (JSON-LD) 생성."""
    import json

    from services.core.ai_metadata import build_faqpage_schema

    schema = build_faqpage_schema(
        (faq['question'], faq['answer']) for faq in faqs
    )
    if schema is None:
        return ''

    return json.dumps(schema, ensure_ascii=False, indent=2)


def _build_faq_markdown(faqs: list) -> str:
    """FAQ 마크다운 생성."""
    lines = ['## 자주 묻는 질문 (FAQ)', '']
    for i, faq in enumerate(faqs, 1):
        lines.append(f'### Q{i}. {faq["question"]}')
        lines.append(f'{faq["answer"]}')
        lines.append('')
    return '\n'.join(lines)


def _generate_suggestions(faqs: list, topics: list) -> list:
    suggestions = []

    if len(faqs) < 3:
        suggestions.append('FAQ가 3개 미만입니다. 콘텐츠에 더 구체적인 정보를 추가하면 더 많은 FAQ를 생성할 수 있습니다.')

    if len(topics) > 8:
        suggestions.append('다양한 주제가 포함되어 있습니다. 주요 주제 3~5개에 집중하면 더 깊은 FAQ가 가능합니다.')

    suggestions.append('생성된 FAQ를 콘텐츠 하단에 추가하면 SEO에 도움이 됩니다 (FAQ 구조화 데이터 포함).')

    return suggestions
