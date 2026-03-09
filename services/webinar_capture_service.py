"""
웨비나 캡처 서비스 — 웨비나 메타데이터 + 요약 생성
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class WebinarCapture:
    """웨비나 캡처 결과"""
    capture_id: str
    title: str
    speakers: list[str]
    duration_min: int
    key_moments: list[dict]
    summary: str
    q_and_a: list[dict]


def capture_webinar(title: str, speakers: list[str], transcript: str, duration: int) -> WebinarCapture:
    """웨비나 캡처 — 키 모먼트 추출 (질문/결론 패턴)"""
    sentences = [s.strip() for s in transcript.replace('\n', '. ').split('.') if s.strip()]
    key_moments = []

    for i, sentence in enumerate(sentences):
        # 질문 패턴
        if '?' in sentence:
            key_moments.append({
                'type': 'question',
                'text': sentence,
                'position': i
            })
        # 결론 패턴
        lower = sentence.lower()
        if any(kw in lower for kw in ['결론', '요약하면', 'in conclusion', 'to summarize', '정리하면', '마무리']):
            key_moments.append({
                'type': 'conclusion',
                'text': sentence,
                'position': i
            })

    # 요약: 처음 + 마지막 문장 결합
    summary_parts = []
    if sentences:
        summary_parts.append(sentences[0])
    if len(sentences) > 1:
        summary_parts.append(sentences[-1])
    summary = '. '.join(summary_parts)

    q_and_a = extract_qa(transcript)

    return WebinarCapture(
        capture_id=str(uuid.uuid4())[:8],
        title=title,
        speakers=speakers,
        duration_min=duration,
        key_moments=key_moments,
        summary=summary,
        q_and_a=q_and_a
    )


def extract_qa(transcript: str) -> list[dict]:
    """Q&A 추출 — ? 포함 문장 + 다음 문장"""
    sentences = [s.strip() for s in transcript.replace('\n', '. ').split('.') if s.strip()]
    qa_list = []

    for i, sentence in enumerate(sentences):
        if '?' in sentence:
            answer = sentences[i + 1] if i + 1 < len(sentences) else ''
            qa_list.append({
                'question': sentence,
                'answer': answer
            })

    return qa_list


def generate_highlights(capture: WebinarCapture, count: int = 3) -> list[dict]:
    """하이라이트 선정 — 질문 키 모먼트 우선, 부족하면 결론"""
    questions = [m for m in capture.key_moments if m['type'] == 'question']
    conclusions = [m for m in capture.key_moments if m['type'] == 'conclusion']

    highlights = []
    for m in questions[:count]:
        highlights.append({'type': m['type'], 'text': m['text']})
    remaining = count - len(highlights)
    if remaining > 0:
        for m in conclusions[:remaining]:
            highlights.append({'type': m['type'], 'text': m['text']})

    return highlights[:count]
