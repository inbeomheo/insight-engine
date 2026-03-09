"""
질문응답 아바타 서비스

영상 지식 텍스트에서 핵심 정보를 추출하고
질문-응답 쌍을 자동 생성하는 규칙 기반 서비스.
외부 API 호출 없음.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid
import re


@dataclass
class QAAvatar:
    """질문응답 아바타."""
    avatar_id: str
    persona: str                      # 전문가 유형
    knowledge_base: List[str]         # 지식 문장 목록
    sample_qa: List[Dict]             # 샘플 질문-응답 쌍
    confidence_threshold: float       # 응답 신뢰도 임계값 (0.0 ~ 1.0)


# ── 페르소나 프리셋 ──
_PERSONA_PRESETS = {
    "expert": {
        "tone": "전문적이고 정확한",
        "greeting": "해당 분야에 대해 깊이 있게 설명해 드리겠습니다.",
        "confidence": 0.7,
    },
    "friendly": {
        "tone": "친근하고 이해하기 쉬운",
        "greeting": "궁금한 점이 있으시면 편하게 물어보세요!",
        "confidence": 0.6,
    },
    "teacher": {
        "tone": "교육적이고 체계적인",
        "greeting": "차근차근 알려드리겠습니다.",
        "confidence": 0.75,
    },
    "concise": {
        "tone": "간결하고 핵심만 전달하는",
        "greeting": "핵심만 짚어드리겠습니다.",
        "confidence": 0.8,
    },
}

# ── 질문 생성 템플릿 ──
_QUESTION_TEMPLATES = [
    "{keyword}에 대해 설명해 주세요.",
    "{keyword}의 주요 특징은 무엇인가요?",
    "{keyword}을(를) 어떻게 활용할 수 있나요?",
    "{keyword}이(가) 중요한 이유는 무엇인가요?",
    "{keyword}의 장단점은 무엇인가요?",
]

# ── 불용어 (질문 생성에서 제외) ──
_STOPWORDS = {
    "그리고", "하지만", "또한", "그래서", "따라서", "그러나", "왜냐하면",
    "이것", "저것", "그것", "여기", "거기", "이런", "그런", "저런",
    "매우", "아주", "정말", "진짜", "좀", "약간", "대략",
    "합니다", "입니다", "됩니다", "있습니다", "없습니다",
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "this", "that", "these", "those", "and", "but", "or", "so",
}

_MIN_SENTENCE_LENGTH = 10   # 최소 문장 길이 (글자)
_MIN_KEYWORD_LENGTH = 2     # 최소 키워드 길이


def _split_sentences(text: str) -> List[str]:
    """텍스트를 문장 단위로 분리."""
    # 마침표, 물음표, 느낌표, 줄바꿈 기준
    sentences = re.split(r'(?<=[.!?。\n])\s*', text.strip())
    result = []
    for s in sentences:
        s = s.strip()
        if len(s) >= _MIN_SENTENCE_LENGTH:
            result.append(s)
    return result


def _extract_keywords(sentences: List[str]) -> List[str]:
    """문장 목록에서 핵심 키워드 추출 (빈도 기반)."""
    word_freq: Dict[str, int] = {}

    for sentence in sentences:
        # 한글+영문 단어 추출
        words = re.findall(r'[가-힣a-zA-Z]{2,}', sentence)
        for word in words:
            if word.lower() not in _STOPWORDS and len(word) >= _MIN_KEYWORD_LENGTH:
                word_freq[word] = word_freq.get(word, 0) + 1

    # 빈도순 정렬, 상위 키워드 반환
    sorted_keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [kw for kw, _ in sorted_keywords[:10]]


def _find_relevant_sentence(keyword: str, sentences: List[str]) -> Optional[str]:
    """키워드가 포함된 가장 적합한 문장 찾기."""
    matches = []
    for s in sentences:
        if keyword in s:
            matches.append(s)

    if not matches:
        return None

    # 가장 긴 문장 선택 (더 많은 정보 포함)
    return max(matches, key=len)


def _generate_qa_pairs(keywords: List[str], sentences: List[str], persona: str) -> List[Dict]:
    """키워드와 문장에서 질문-응답 쌍 생성."""
    preset = _PERSONA_PRESETS.get(persona, _PERSONA_PRESETS["expert"])
    tone = preset["tone"]
    pairs = []

    for i, keyword in enumerate(keywords):
        if len(pairs) >= 5:  # 최대 5개 QA 쌍
            break

        # 관련 문장 찾기
        relevant = _find_relevant_sentence(keyword, sentences)
        if not relevant:
            continue

        # 질문 템플릿 선택 (순환)
        template = _QUESTION_TEMPLATES[i % len(_QUESTION_TEMPLATES)]
        question = template.format(keyword=keyword)

        # 답변 구성 (관련 문장 + 톤 적용)
        answer = relevant

        # 신뢰도 계산 (키워드 빈도와 문장 길이 기반)
        keyword_count = sum(1 for s in sentences if keyword in s)
        confidence = min(0.95, 0.5 + (keyword_count * 0.1) + (len(relevant) / 500))

        pairs.append({
            "question": question,
            "answer": answer,
            "keyword": keyword,
            "confidence": round(confidence, 2),
        })

    return pairs


def create_qa_avatar(video_knowledge: str, persona: str = "expert") -> QAAvatar:
    """
    질문응답 아바타를 생성한다.

    Args:
        video_knowledge: 영상에서 추출된 지식 텍스트 (자막, 요약 등)
        persona: 아바타 성격 ("expert", "friendly", "teacher", "concise")

    Returns:
        QAAvatar: QA 아바타 (지식 베이스 + 샘플 QA)

    Raises:
        ValueError: 지식 텍스트가 비어있을 때
    """
    if not video_knowledge or not video_knowledge.strip():
        raise ValueError("영상 지식 텍스트가 필요합니다")

    # 유효한 페르소나 확인 (기본값: expert)
    if persona not in _PERSONA_PRESETS:
        persona = "expert"

    preset = _PERSONA_PRESETS[persona]

    # 문장 분리 → 지식 베이스 구성
    sentences = _split_sentences(video_knowledge)
    if not sentences:
        # 문장 분리 실패 시 전체 텍스트를 하나의 지식으로
        sentences = [video_knowledge.strip()]

    knowledge_base = sentences

    # 키워드 추출
    keywords = _extract_keywords(sentences)

    # QA 쌍 생성
    sample_qa = _generate_qa_pairs(keywords, sentences, persona)

    # 신뢰도 임계값
    confidence_threshold = preset["confidence"]

    return QAAvatar(
        avatar_id=str(uuid.uuid4())[:12],
        persona=persona,
        knowledge_base=knowledge_base,
        sample_qa=sample_qa,
        confidence_threshold=confidence_threshold,
    )
