"""
질문 트리 서비스

콘텐츠에서 핵심 주제를 추출하고,
"왜?/어떻게?/무엇을?" 후속 질문을 재귀적으로 확장합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional
from collections import Counter


@dataclass
class QuestionNode:
    """질문 트리의 개별 노드"""
    question: str                          # 질문 텍스트
    level: int                             # 트리 깊이 (0 = 루트)
    parent_question: Optional[str]         # 부모 질문 (루트는 None)
    children: List[str] = field(default_factory=list)   # 자식 질문 텍스트 목록
    answer_hint: str = ""                  # 답변 힌트 (원문에서 추출)


@dataclass
class QuestionTree:
    """질문 트리 전체 구조"""
    root_topic: str                        # 루트 주제
    nodes: List[QuestionNode] = field(default_factory=list)  # 전체 노드 목록
    total_questions: int = 0               # 총 질문 수
    depth: int = 0                         # 트리 깊이


# ── 불용어 (주제 추출 시 제외) ──

_STOPWORDS_KO = frozenset([
    '그리고', '하지만', '그러나', '또한', '때문에', '그래서', '따라서',
    '이것', '저것', '그것', '여기', '거기', '이런', '그런', '저런',
    '있다', '없다', '하다', '되다', '것이다', '수있다', '합니다',
    '입니다', '습니다', '에서', '으로', '부터', '까지', '대한',
    '통해', '위해', '관한', '통한', '위한', '같은', '다른',
])

_STOPWORDS_EN = frozenset([
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'shall', 'and', 'or', 'but', 'if',
    'then', 'so', 'that', 'this', 'these', 'those', 'it', 'its',
    'of', 'in', 'to', 'for', 'with', 'on', 'at', 'by', 'from', 'as',
    'not', 'no', 'very', 'just', 'also', 'about', 'more', 'some',
])

# ── 질문 생성 템플릿 ──

_QUESTION_TEMPLATES_KO = {
    'why': [
        '{topic}이(가) 왜 중요한가?',
        '{topic}의 근본적인 이유는 무엇인가?',
        '{topic}이(가) 필요한 이유는?',
    ],
    'how': [
        '{topic}을(를) 어떻게 구현하는가?',
        '{topic}의 작동 원리는 무엇인가?',
        '{topic}을(를) 어떻게 개선할 수 있는가?',
    ],
    'what': [
        '{topic}의 핵심 요소는 무엇인가?',
        '{topic}의 장단점은 무엇인가?',
        '{topic}과(와) 관련된 주요 개념은?',
    ],
}

_QUESTION_TEMPLATES_EN = {
    'why': [
        'Why is {topic} important?',
        'What is the fundamental reason for {topic}?',
        'Why do we need {topic}?',
    ],
    'how': [
        'How does {topic} work?',
        'How can {topic} be implemented?',
        'How can {topic} be improved?',
    ],
    'what': [
        'What are the key elements of {topic}?',
        'What are the pros and cons of {topic}?',
        'What concepts are related to {topic}?',
    ],
}


def _detect_language(text: str) -> str:
    """텍스트의 주 언어를 감지합니다 (ko/en)."""
    ko_chars = len(re.findall(r'[가-힣]', text))
    en_chars = len(re.findall(r'[a-zA-Z]', text))
    return 'ko' if ko_chars >= en_chars else 'en'


def _extract_sentences(text: str) -> List[str]:
    """텍스트를 문장 단위로 분리합니다."""
    # 마침표/물음표/느낌표/줄바꿈 기준 분리
    sentences = re.split(r'(?<=[.!?。])\s+|\n+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]


def _extract_key_phrases(text: str, lang: str, max_phrases: int = 5) -> List[str]:
    """텍스트에서 핵심 구문(주제)을 추출합니다.

    명사구/키워드 빈도 기반으로 상위 구문을 반환합니다.
    """
    stopwords = _STOPWORDS_KO if lang == 'ko' else _STOPWORDS_EN

    if lang == 'ko':
        # 한국어: 2~6자 한글 단어 추출
        words = re.findall(r'[가-힣]{2,6}', text)
    else:
        # 영어: 공백 기준 단어 추출 (소문자 변환)
        raw_words = re.findall(r'[a-zA-Z]{3,}', text)
        words = [w.lower() for w in raw_words]

    # 불용어 제거
    filtered = [w for w in words if w.lower() not in stopwords and len(w) > 1]

    if not filtered:
        return []

    # 빈도 기반 상위 구문 추출
    counter = Counter(filtered)
    top_phrases = [phrase for phrase, _ in counter.most_common(max_phrases)]
    return top_phrases


def _find_hint_for_topic(sentences: List[str], topic: str) -> str:
    """주제와 관련된 문장에서 답변 힌트를 추출합니다."""
    topic_lower = topic.lower()
    for sent in sentences:
        if topic_lower in sent.lower():
            # 최대 100자까지 힌트로 사용
            hint = sent[:100].strip()
            if len(sent) > 100:
                hint += '...'
            return hint
    return ""


def _generate_questions_for_topic(
    topic: str,
    lang: str,
    category: str,
) -> str:
    """주제와 카테고리에 맞는 질문을 생성합니다.

    Args:
        topic: 주제 키워드
        lang: 언어 (ko/en)
        category: 질문 유형 (why/how/what)

    Returns:
        생성된 질문 텍스트
    """
    templates = _QUESTION_TEMPLATES_KO if lang == 'ko' else _QUESTION_TEMPLATES_EN

    if category not in templates:
        category = 'what'

    # 카테고리 내 템플릿을 주제 길이 기반으로 선택 (결정적)
    template_list = templates[category]
    idx = len(topic) % len(template_list)
    return template_list[idx].format(topic=topic)


def _build_tree_recursive(
    topics: List[str],
    sentences: List[str],
    lang: str,
    current_depth: int,
    max_depth: int,
    parent_question: Optional[str],
    nodes: List[QuestionNode],
) -> None:
    """재귀적으로 질문 트리를 확장합니다.

    Args:
        topics: 현재 단계의 주제 목록
        sentences: 원본 문장 목록 (힌트 추출용)
        lang: 언어 (ko/en)
        current_depth: 현재 깊이
        max_depth: 최대 깊이
        parent_question: 부모 질문 텍스트
        nodes: 노드를 추가할 리스트 (in-place 변경)
    """
    if current_depth >= max_depth or not topics:
        return

    categories = ['why', 'how', 'what']

    for topic in topics:
        # 각 주제에 대해 3가지 유형(왜/어떻게/무엇) 질문 생성
        child_questions = []
        for cat in categories:
            question_text = _generate_questions_for_topic(topic, lang, cat)
            child_questions.append(question_text)

        hint = _find_hint_for_topic(sentences, topic)

        # 부모 노드 생성
        node = QuestionNode(
            question=_generate_questions_for_topic(topic, lang, categories[current_depth % 3]),
            level=current_depth,
            parent_question=parent_question,
            children=child_questions,
            answer_hint=hint,
        )
        nodes.append(node)

        # 자식 질문에서 새 주제 추출 → 재귀 확장
        # 다음 깊이에서는 주제를 파생시킴 (원래 주제의 하위 개념)
        if current_depth + 1 < max_depth:
            # 자식 질문들에서 핵심 단어 추출하여 하위 주제로 사용
            child_text = ' '.join(child_questions)
            sub_topics = _extract_key_phrases(child_text, lang, max_phrases=2)
            # 이미 사용된 주제와 겹치지 않는 것만 선택
            existing_topics = {t.lower() for t in topics}
            sub_topics = [t for t in sub_topics if t.lower() not in existing_topics]

            if sub_topics:
                for child_q in child_questions[:1]:  # 첫 번째 자식만 재귀 확장
                    _build_tree_recursive(
                        topics=sub_topics[:1],
                        sentences=sentences,
                        lang=lang,
                        current_depth=current_depth + 1,
                        max_depth=max_depth,
                        parent_question=child_q,
                        nodes=nodes,
                    )


def expand_question_tree(content: str, depth: int = 3) -> QuestionTree:
    """콘텐츠에서 질문 트리를 확장합니다.

    Args:
        content: 분석할 콘텐츠 텍스트
        depth: 트리 최대 깊이 (기본 3)

    Returns:
        확장된 QuestionTree
    """
    if not content or not content.strip():
        return QuestionTree(root_topic="", nodes=[], total_questions=0, depth=0)

    # depth 범위 제한 (1~5)
    depth = max(1, min(5, depth))

    lang = _detect_language(content)
    sentences = _extract_sentences(content)
    topics = _extract_key_phrases(content, lang, max_phrases=5)

    if not topics:
        return QuestionTree(root_topic="", nodes=[], total_questions=0, depth=0)

    root_topic = topics[0]
    nodes: List[QuestionNode] = []

    _build_tree_recursive(
        topics=topics,
        sentences=sentences,
        lang=lang,
        current_depth=0,
        max_depth=depth,
        parent_question=None,
        nodes=nodes,
    )

    # 총 질문 수 = 노드 수 + 모든 자식 질문 수
    total_questions = len(nodes) + sum(len(n.children) for n in nodes)
    actual_depth = max((n.level for n in nodes), default=0) + 1 if nodes else 0

    return QuestionTree(
        root_topic=root_topic,
        nodes=nodes,
        total_questions=total_questions,
        depth=actual_depth,
    )
