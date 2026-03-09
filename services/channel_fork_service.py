"""
채널별 분기 + 숏폼 리퍼포징 서비스

장문 콘텐츠를 채널(twitter, linkedin, instagram, blog, newsletter)별
톤/길이에 맞게 분기 생성하고, 스레드/카드뉴스/이메일 티저 등 숏폼으로 분해한다.

순수 Python 구현 — AI 호출 없이 텍스트 가공만 수행.
"""
import re
import textwrap
from dataclasses import dataclass, field
from typing import Dict, List


# ── 채널 설정 ──────────────────────────────────────────────

@dataclass
class ChannelConfig:
    """채널별 생성 규칙"""
    name: str                    # "twitter" | "linkedin" | "instagram" | "blog" | "newsletter"
    max_length: int              # 최대 글자수
    tone: str                    # "casual" | "professional" | "friendly"
    hashtag_count: int = 0       # 해시태그 개수 (0이면 생략)


# 기본 채널 프리셋
DEFAULT_CHANNELS: Dict[str, ChannelConfig] = {
    "twitter": ChannelConfig(name="twitter", max_length=280, tone="casual", hashtag_count=3),
    "linkedin": ChannelConfig(name="linkedin", max_length=1300, tone="professional", hashtag_count=5),
    "instagram": ChannelConfig(name="instagram", max_length=2200, tone="friendly", hashtag_count=10),
    "blog": ChannelConfig(name="blog", max_length=5000, tone="professional", hashtag_count=0),
    "newsletter": ChannelConfig(name="newsletter", max_length=3000, tone="friendly", hashtag_count=0),
}


# ── 결과 데이터 ──────────────────────────────────────────────

@dataclass
class ChannelPost:
    """채널별 변환 결과"""
    channel: str
    content: str
    hashtags: List[str]
    char_count: int
    word_count: int


@dataclass
class RepurposePack:
    """장문 → 숏폼 분해 결과 (3포맷+)"""
    thread: List[str]            # 트위터 스레드 (280자씩)
    card_news: List[dict]        # 카드뉴스 슬라이드 [{title, body}]
    email_teaser: str            # 이메일 티저
    summary: str                 # 한줄 요약


# ── 내부 헬퍼 ──────────────────────────────────────────────

def _extract_sentences(text: str) -> List[str]:
    """텍스트를 문장 단위로 분리한다.

    마침표/물음표/느낌표 뒤 공백 또는 줄바꿈을 기준으로 분리.
    빈 문장은 제거한다.
    """
    # 마크다운 헤더(#), 리스트(- *) 제거
    cleaned = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    cleaned = re.sub(r'(?:^|\s)[\-\*]\s+', ' ', cleaned)
    cleaned = cleaned.strip()

    if not cleaned:
        return []

    # 문장 분리: 마침표/물음표/느낌표 뒤에 공백이나 줄바꿈이 오면 분리
    sentences = re.split(r'(?<=[.?!。])\s+', cleaned)
    return [s.strip() for s in sentences if s.strip()]


def _extract_keywords(text: str, count: int) -> List[str]:
    """텍스트에서 빈도 기반 키워드를 추출하여 해시태그로 반환한다.

    2글자 이상의 한글/영문 단어를 빈도순으로 정렬한 뒤 상위 count개를 반환.
    """
    if count <= 0:
        return []

    # 한글, 영문 단어만 추출 (2글자 이상)
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', text)
    # 불용어 제거 (한국어/영어 기본 불용어)
    stopwords = {
        '그리고', '하지만', '그래서', '때문에', '이것은', '그것은', '하는',
        '있는', '없는', '되는', '하고', '에서', '으로', '에게', '부터',
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are',
    }
    filtered = [w for w in words if w.lower() not in stopwords]

    # 빈도 계산
    freq: Dict[str, int] = {}
    for w in filtered:
        key = w.lower()
        freq[key] = freq.get(key, 0) + 1

    # 빈도순 정렬 후 상위 count개
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:count]]


def _adjust_tone(text: str, tone: str) -> str:
    """톤에 따라 텍스트 문체를 조정한다.

    - casual: 구어체/축약형 유지
    - professional: 공식 문체 (~입니다/~합니다)
    - friendly: 부드러운 톤 (~해요/~에요)
    """
    if tone == "casual":
        # ~입니다 → ~임, ~합니다 → ~함
        text = re.sub(r'합니다', '함', text)
        text = re.sub(r'입니다', '임', text)
        text = re.sub(r'됩니다', '됨', text)
        text = re.sub(r'습니다', '', text)
    elif tone == "friendly":
        # ~합니다 → ~해요, ~입니다 → ~이에요
        text = re.sub(r'합니다', '해요', text)
        text = re.sub(r'입니다', '이에요', text)
        text = re.sub(r'됩니다', '돼요', text)
    # professional은 원본 유지

    return text


def _truncate(text: str, max_length: int) -> str:
    """텍스트를 max_length 이내로 자른다.

    초과 시 마지막 문장 경계에서 자르고 '...'을 추가한다.
    """
    if len(text) <= max_length:
        return text

    # 여유 공간 확보 (말줄임표 3자)
    limit = max_length - 3
    if limit <= 0:
        return text[:max_length]

    # 마지막 문장 경계 찾기
    truncated = text[:limit]
    last_period = max(truncated.rfind('.'), truncated.rfind('!'),
                      truncated.rfind('?'), truncated.rfind('。'))
    if last_period > limit // 2:
        truncated = truncated[:last_period + 1]

    return truncated + '...'


# ── 공개 API ──────────────────────────────────────────────

def fork_for_channels(
    content: str,
    channels: List[dict],
) -> Dict[str, ChannelPost]:
    """콘텐츠를 채널별 톤/길이로 분기 생성한다.

    Args:
        content: 원본 장문 콘텐츠
        channels: 채널 설정 리스트. 각 항목은 ChannelConfig 필드와 동일한 dict.
                  예: [{"name": "twitter", "max_length": 280, "tone": "casual", "hashtag_count": 3}]

    Returns:
        채널명 → ChannelPost 매핑 dict

    Raises:
        ValueError: content가 비어있거나 channels가 빈 리스트일 때
    """
    if not content or not content.strip():
        raise ValueError("콘텐츠가 비어있습니다")
    if not channels:
        raise ValueError("채널 목록이 비어있습니다")

    results: Dict[str, ChannelPost] = {}

    for ch_dict in channels:
        config = ChannelConfig(**ch_dict)

        # 1. 톤 조정
        adjusted = _adjust_tone(content.strip(), config.tone)

        # 2. 글자수 제한 적용
        hashtag_suffix = ""
        if config.hashtag_count > 0:
            tags = _extract_keywords(content, config.hashtag_count)
            hashtag_suffix = " " + " ".join(f"#{t}" for t in tags)
            # 해시태그 공간을 제외한 본문 최대 길이
            body_max = config.max_length - len(hashtag_suffix)
        else:
            tags = []
            body_max = config.max_length

        truncated = _truncate(adjusted, max(body_max, 10))
        final_content = truncated + hashtag_suffix

        # 3. 단어수 계산
        word_count = len(re.findall(r'\S+', truncated))

        results[config.name] = ChannelPost(
            channel=config.name,
            content=final_content,
            hashtags=tags,
            char_count=len(final_content),
            word_count=word_count,
        )

    return results


def repurpose_longform(content: str) -> RepurposePack:
    """장문 콘텐츠를 스레드/카드뉴스/이메일 티저로 분해한다 (3포맷+).

    AI 호출 없이 순수 텍스트 가공으로 동작한다.

    Args:
        content: 원본 장문 콘텐츠 (마크다운 가능)

    Returns:
        RepurposePack (thread, card_news, email_teaser, summary)

    Raises:
        ValueError: content가 비어있을 때
    """
    if not content or not content.strip():
        raise ValueError("콘텐츠가 비어있습니다")

    sentences = _extract_sentences(content)
    if not sentences:
        raise ValueError("유효한 문장이 없습니다")

    # ── 1. 트위터 스레드 (280자씩 분할) ──
    thread = _build_thread(sentences, max_chars=280)

    # ── 2. 카드뉴스 슬라이드 (3~7장) ──
    card_news = _build_card_news(sentences)

    # ── 3. 이메일 티저 (200자 이내 요약 + CTA) ──
    email_teaser = _build_email_teaser(sentences)

    # ── 4. 한줄 요약 (첫 문장 기반) ──
    summary = _build_summary(sentences)

    return RepurposePack(
        thread=thread,
        card_news=card_news,
        email_teaser=email_teaser,
        summary=summary,
    )


def _build_thread(sentences: List[str], max_chars: int = 280) -> List[str]:
    """문장들을 280자 이내 트윗 단위로 묶는다."""
    tweets: List[str] = []
    current = ""

    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                tweets.append(current)
            # 단일 문장이 max_chars 초과 시 강제 분할
            if len(sentence) > max_chars:
                chunks = textwrap.wrap(sentence, width=max_chars)
                tweets.extend(chunks)
                current = ""
            else:
                current = sentence

    if current:
        tweets.append(current)

    # 최소 1개 보장
    return tweets if tweets else [sentences[0][:max_chars]]


def _build_card_news(sentences: List[str]) -> List[dict]:
    """문장들을 카드뉴스 슬라이드로 묶는다.

    슬라이드 구조: {title: str, body: str}
    3~7장, 각 슬라이드 body는 2~4문장.
    """
    target_slides = min(max(len(sentences) // 3, 3), 7)
    chunk_size = max(len(sentences) // target_slides, 1)

    slides: List[dict] = []
    for i in range(0, len(sentences), chunk_size):
        chunk = sentences[i:i + chunk_size]
        if not chunk:
            continue
        # 첫 문장을 제목으로, 나머지를 본문으로
        title = chunk[0][:50]  # 제목 50자 제한
        body = " ".join(chunk)
        slides.append({"title": title, "body": body})
        if len(slides) >= 7:
            break

    # 최소 1장 보장
    if not slides:
        slides.append({"title": sentences[0][:50], "body": sentences[0]})

    return slides


def _build_email_teaser(sentences: List[str]) -> str:
    """이메일 티저: 핵심 2~3문장 + CTA 문구."""
    # 상위 2~3 문장 선택
    teaser_sentences = sentences[:3]
    teaser_body = " ".join(teaser_sentences)

    # 200자 제한
    if len(teaser_body) > 180:
        teaser_body = teaser_body[:177] + "..."

    cta = "\n\n전체 내용이 궁금하다면 지금 확인해보세요."
    return teaser_body + cta


def _build_summary(sentences: List[str]) -> str:
    """한줄 요약: 첫 문장 기반, 100자 이내."""
    first = sentences[0]
    if len(first) <= 100:
        return first
    # 100자 내에서 마지막 구두점 찾기
    truncated = first[:97]
    last_period = max(truncated.rfind('.'), truncated.rfind('!'),
                      truncated.rfind('?'))
    if last_period > 50:
        return truncated[:last_period + 1]
    return truncated + "..."
