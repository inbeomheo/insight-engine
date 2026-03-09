"""
속보 브리지 서비스

속보 콘텐츠를 즉시반응용 짧은 글 + 검색형 장문 해설 세트로 변환합니다.
핵심 사실 추출, 타임라인 구성, 후속 질문 생성을 포함합니다.
"""
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 즉시 반응 글 최대 길이
_INSTANT_MAX_LENGTH = 200

# 시간 표현 패턴 (타임라인 추출용)
_TIME_PATTERNS = [
    r'(\d{1,2}월\s*\d{1,2}일)',
    r'(\d{4}년\s*\d{1,2}월)',
    r'(\d{1,2}시\s*\d{0,2}분?)',
    r'(오전|오후)\s*\d{1,2}시',
    r'(어제|오늘|내일|그저께|모레)',
    r'(지난\s*(주|달|해|월|년))',
    r'(이번\s*(주|달|월))',
    r'(\d+일\s*전)',
    r'(\d+시간\s*전)',
]

# 사실 문장 지표 (핵심 사실 추출용)
_FACT_INDICATORS = [
    r'으로\s*확인',
    r'것으로\s*알려',
    r'것으로\s*나타',
    r'것으로\s*밝혀',
    r'에\s*따르면',
    r'라고\s*(밝혔|말했|전했|발표|설명)',
    r'로\s*집계',
    r'을\s*발표',
    r'이\s*발생',
    r'가\s*확인',
    r'\d+[명건개억만]',
]

# 후속 질문 템플릿
_FOLLOW_UP_TEMPLATES = [
    "이 사건의 근본 원인은 무엇인가?",
    "향후 전개 방향은 어떻게 될 것인가?",
    "관련 당사자들의 공식 입장은?",
    "유사 사례와 비교했을 때 차이점은?",
    "이로 인한 파급 효과는 어디까지인가?",
]


@dataclass
class BridgePack:
    """속보 브리지 패키지: 즉시반응 + 검색형 해설 세트"""
    instant_reaction: str        # 즉시 반응 짧은 글 (200자 이내)
    deep_analysis: str           # 검색형 장문 해설
    key_facts: list[str]         # 핵심 사실 3개+
    timeline: list[dict]         # [{"time": "...", "event": "..."}]
    follow_up_questions: list[str] = field(default_factory=list)


def generate_bridge(breaking_content: str) -> BridgePack:
    """속보 콘텐츠에서 즉시반응 + 검색형 해설 세트를 생성합니다.

    Args:
        breaking_content: 속보 원문 텍스트

    Returns:
        BridgePack 데이터클래스

    Raises:
        ValueError: 콘텐츠가 비어있거나 유효하지 않을 때
    """
    if not breaking_content or not breaking_content.strip():
        raise ValueError("속보 콘텐츠가 비어 있습니다.")

    content = breaking_content.strip()
    sentences = _split_sentences(content)

    if not sentences:
        raise ValueError("분석할 문장이 없습니다.")

    # 1. 핵심 사실 추출
    key_facts = _extract_key_facts(sentences)

    # 2. 타임라인 구성
    timeline = _extract_timeline(sentences)

    # 3. 즉시 반응 글 생성 (200자 이내)
    instant_reaction = _build_instant_reaction(sentences, key_facts)

    # 4. 검색형 장문 해설 생성
    deep_analysis = _build_deep_analysis(sentences, key_facts, timeline)

    # 5. 후속 질문 생성
    follow_up_questions = _generate_follow_up_questions(content, key_facts)

    return BridgePack(
        instant_reaction=instant_reaction,
        deep_analysis=deep_analysis,
        key_facts=key_facts,
        timeline=timeline,
        follow_up_questions=follow_up_questions,
    )


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리합니다."""
    # 줄바꿈 + 마침표/물음표/느낌표 기준 분리
    raw = re.split(r'(?<=[.!?。])\s+|\n+', text)
    return [s.strip() for s in raw if len(s.strip()) >= 5]


def _extract_key_facts(sentences: list[str]) -> list[str]:
    """문장 목록에서 핵심 사실을 추출합니다. 최소 3개 반환."""
    scored = []

    for sentence in sentences:
        score = 0
        # 사실 지표 매칭
        for pattern in _FACT_INDICATORS:
            if re.search(pattern, sentence):
                score += 2

        # 숫자 포함 (구체적 사실)
        if re.search(r'\d+', sentence):
            score += 1

        # 인용 부호 포함 (발언 인용)
        if re.search(r'[""\'\'「」]', sentence):
            score += 1

        # 너무 짧은 문장 감점
        if len(sentence) < 15:
            score -= 1

        scored.append((sentence, score))

    # 점수 내림차순 정렬
    scored.sort(key=lambda x: x[1], reverse=True)

    # 최소 3개 보장
    facts = [s for s, _ in scored[:max(3, min(5, len(scored)))]]

    # 문장이 3개 미만이면 원래 문장 그대로 반환
    if len(facts) < 3 and len(sentences) >= 1:
        facts = list(sentences[:3]) if len(sentences) >= 3 else list(sentences)

    return facts


def _extract_timeline(sentences: list[str]) -> list[dict]:
    """문장에서 시간 정보를 추출하여 타임라인을 구성합니다."""
    timeline = []

    for sentence in sentences:
        for pattern in _TIME_PATTERNS:
            match = re.search(pattern, sentence)
            if match:
                time_str = match.group(0).strip()
                # 시간 부분 제거한 나머지를 이벤트로
                event = sentence.strip()
                timeline.append({
                    "time": time_str,
                    "event": event,
                })
                break  # 한 문장에서 첫 번째 시간만

    # 중복 제거
    seen = set()
    unique_timeline = []
    for item in timeline:
        key = item["event"]
        if key not in seen:
            seen.add(key)
            unique_timeline.append(item)

    return unique_timeline


def _build_instant_reaction(sentences: list[str], key_facts: list[str]) -> str:
    """즉시 반응용 짧은 글을 생성합니다 (200자 이내).

    첫 번째 핵심 사실을 중심으로 구성합니다.
    """
    if not key_facts:
        # 핵심 사실이 없으면 첫 문장 기반
        base = sentences[0] if sentences else ""
    else:
        base = key_facts[0]

    # 200자 이내로 자르기
    if len(base) <= _INSTANT_MAX_LENGTH:
        result = base
    else:
        # 마지막 마침표/공백 기준으로 자르기
        truncated = base[:_INSTANT_MAX_LENGTH]
        last_period = max(truncated.rfind('.'), truncated.rfind('다.'))
        if last_period > _INSTANT_MAX_LENGTH // 2:
            result = truncated[:last_period + 1]
        else:
            result = truncated.rstrip() + '...'

    return result


def _build_deep_analysis(
    sentences: list[str],
    key_facts: list[str],
    timeline: list[dict],
) -> str:
    """검색형 장문 해설을 마크다운 형식으로 생성합니다."""
    parts = []

    # 제목 (첫 문장 기반)
    title = sentences[0] if sentences else "속보 분석"
    if len(title) > 50:
        title = title[:50] + '...'
    parts.append(f"# {title}\n")

    # 핵심 요약
    parts.append("## 핵심 요약\n")
    for i, fact in enumerate(key_facts, 1):
        parts.append(f"{i}. {fact}")
    parts.append("")

    # 타임라인 (있을 경우)
    if timeline:
        parts.append("## 타임라인\n")
        for item in timeline:
            parts.append(f"- **{item['time']}**: {item['event']}")
        parts.append("")

    # 상세 분석 (전체 문장)
    parts.append("## 상세 내용\n")
    for sentence in sentences:
        parts.append(sentence)
    parts.append("")

    return "\n".join(parts)


def _generate_follow_up_questions(content: str, key_facts: list[str]) -> list[str]:
    """콘텐츠와 핵심 사실 기반으로 후속 질문을 생성합니다."""
    questions = []

    # 주제어 추출
    topic_words = _extract_topic_words(content)

    # 기본 템플릿에서 선택
    questions.extend(_FOLLOW_UP_TEMPLATES[:3])

    # 주제어 기반 맞춤 질문 추가
    if topic_words:
        main_topic = topic_words[0]
        questions.append(f"{main_topic}과(와) 관련된 추가 정보는?")

    # 숫자가 포함된 사실이 있으면 비교 질문
    for fact in key_facts:
        if re.search(r'\d+', fact):
            questions.append("이전 수치와 비교하면 어떤 변화가 있는가?")
            break

    return questions


def _extract_topic_words(text: str) -> list[str]:
    """텍스트에서 주요 주제어를 추출합니다."""
    words = re.findall(r'[가-힣]{2,6}', text)
    freq: dict[str, int] = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    # 불용어 제외
    stopwords = {
        '있습니다', '합니다', '입니다', '됩니다', '것으로', '대해서',
        '위해서', '통해서', '대한', '하는', '이는', '라고', '것이',
        '에서', '으로', '에게', '까지', '부터',
    }

    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words if w not in stopwords][:5]
