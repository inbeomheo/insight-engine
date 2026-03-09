"""
고객 지원 자산팩 생성 서비스

고객 지원/교육 영상의 자막에서
FAQ, 문제 해결 단계, 퀵 레퍼런스 카드, 교육 아웃라인을 자동 생성합니다.
"""
import hashlib
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CsAssetPack:
    """고객 지원 자산팩"""
    video_id: str
    faq_items: list[dict] = field(default_factory=list)           # FAQ [{"q": "...", "a": "..."}]
    troubleshoot_steps: list[dict] = field(default_factory=list)  # 문제 해결 단계
    quick_reference: str = ""                                      # 퀵 레퍼런스 카드
    training_outline: list[str] = field(default_factory=list)     # 교육 아웃라인


def build_cs_pack(transcript: str, video_id: str = "") -> CsAssetPack:
    """지원 영상 자막에서 CS 자산팩을 생성합니다.

    Args:
        transcript: 영상 자막 텍스트
        video_id: 영상 식별자 (선택)

    Returns:
        CsAssetPack 데이터클래스 (FAQ 5개+ 포함)
    """
    if not transcript or not transcript.strip():
        return CsAssetPack(video_id=video_id or "")

    clean = _strip_markup(transcript)
    sentences = _split_sentences(clean)

    if not sentences:
        return CsAssetPack(video_id=video_id or "")

    vid = video_id or hashlib.md5(clean[:100].encode()).hexdigest()[:8]

    faq_items = _extract_faq(sentences)
    troubleshoot_steps = _extract_troubleshoot(sentences)
    quick_reference = _build_quick_reference(sentences)
    training_outline = _build_training_outline(sentences)

    return CsAssetPack(
        video_id=vid,
        faq_items=faq_items,
        troubleshoot_steps=troubleshoot_steps,
        quick_reference=quick_reference,
        training_outline=training_outline,
    )


# ── 전처리 유틸리티 ──

def _strip_markup(text: str) -> str:
    """마크다운/HTML 태그를 제거합니다."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리합니다."""
    raw = re.split(r'[.!?。]\s*|\n+', text)
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s) >= 8:
            sentences.append(s)
    return sentences


# ── FAQ 추출 ──

# 질문/답변 감지 패턴
_QA_PATTERNS = [
    re.compile(r'(.+?)[?？]\s*(.+)', re.DOTALL),
]

_FAQ_TRIGGER_KEYWORDS = [
    '어떻게', '왜', '무엇', '언제', '어디', '누가',
    '방법', '원인', '해결', '문제', '오류', '에러',
    'how', 'why', 'what', 'when', 'where', 'error',
]

_FAQ_ANSWER_KEYWORDS = [
    '하세요', '합니다', '됩니다', '입니다', '있습니다',
    '해야', '하면', '클릭', '선택', '설정', '확인',
]


def _extract_faq(sentences: list[str]) -> list[dict]:
    """문장 목록에서 FAQ를 추출합니다. 최소 5개를 보장합니다."""
    faqs = []
    used = set()

    # 1차: 질문형 문장에서 직접 추출
    for i, s in enumerate(sentences):
        if len(faqs) >= 10:
            break
        if _is_question_like(s) and i not in used:
            answer = _find_answer(sentences, i)
            if answer:
                faqs.append({"q": _format_question(s), "a": answer})
                used.add(i)

    # 2차: 키워드 기반 문장을 질문으로 변환 (5개 미만이면 보충)
    if len(faqs) < 5:
        for i, s in enumerate(sentences):
            if len(faqs) >= 8:
                break
            if i in used:
                continue
            if _contains_actionable_info(s):
                q = _sentence_to_question(s)
                if q:
                    faqs.append({"q": q, "a": s})
                    used.add(i)

    # 3차: 긴 설명 문장에서 추가 생성 (여전히 5개 미만이면)
    if len(faqs) < 5:
        for i, s in enumerate(sentences):
            if len(faqs) >= 5:
                break
            if i in used:
                continue
            if len(s) >= 20:
                topic = _extract_sentence_topic(s)
                if topic:
                    faqs.append({
                        "q": f"{topic}에 대해 알려주세요.",
                        "a": s,
                    })
                    used.add(i)

    return faqs


def _is_question_like(sentence: str) -> bool:
    """문장이 질문 형태인지 판별합니다."""
    if '?' in sentence or '？' in sentence:
        return True
    return any(kw in sentence for kw in _FAQ_TRIGGER_KEYWORDS[:6])


def _find_answer(sentences: list[str], q_idx: int) -> str:
    """질문 바로 뒤의 문장에서 답변을 찾습니다."""
    # 뒤 3문장 중 답변 키워드가 포함된 것을 사용
    for offset in range(1, min(4, len(sentences) - q_idx)):
        candidate = sentences[q_idx + offset]
        if any(kw in candidate for kw in _FAQ_ANSWER_KEYWORDS):
            return candidate
    # 못 찾으면 바로 다음 문장
    if q_idx + 1 < len(sentences):
        return sentences[q_idx + 1]
    return ""


def _contains_actionable_info(sentence: str) -> bool:
    """문장이 실행 가능한 정보를 포함하는지 판별합니다."""
    return any(kw in sentence for kw in _FAQ_ANSWER_KEYWORDS)


def _sentence_to_question(sentence: str) -> str:
    """서술형 문장을 질문 형태로 변환합니다."""
    # "X를 하세요" → "X를 하려면 어떻게 하나요?"
    if any(kw in sentence for kw in ['하세요', '해야', '하면']):
        topic = _extract_sentence_topic(sentence)
        if topic:
            return f"{topic}은(는) 어떻게 하나요?"

    # "X가 됩니다" → "X는 무엇인가요?"
    if any(kw in sentence for kw in ['됩니다', '입니다', '있습니다']):
        topic = _extract_sentence_topic(sentence)
        if topic:
            return f"{topic}은(는) 무엇인가요?"

    return ""


def _format_question(text: str) -> str:
    """질문 텍스트를 정돈합니다."""
    text = text.strip()
    if not text.endswith('?') and not text.endswith('？'):
        text += '?'
    return text


def _extract_sentence_topic(sentence: str) -> str:
    """문장에서 핵심 주제어(2~15자)를 추출합니다."""
    # 한글 명사구 추출 (조사 앞 단어)
    matches = re.findall(r'([가-힣a-zA-Z0-9]{2,15})[을를은는이가의에]', sentence)
    if matches:
        return matches[0]
    # 영어 단어
    eng = re.findall(r'[A-Za-z]{3,15}', sentence)
    if eng:
        return eng[0]
    # 앞 15자
    if len(sentence) >= 5:
        return sentence[:15].strip()
    return ""


# ── 문제 해결 단계 추출 ──

_STEP_KEYWORDS = [
    '먼저', '다음', '그리고', '그 후', '마지막',
    '1단계', '2단계', '3단계', '4단계', '5단계',
    '첫째', '둘째', '셋째', '넷째',
    '클릭', '선택', '입력', '확인', '설정', '실행',
    'step', 'click', 'select', 'enter', 'check',
]

_PROBLEM_KEYWORDS = [
    '문제', '오류', '에러', '안 되', '안되', '실패',
    '해결', '원인', '증상', '발생', '현상',
    'error', 'problem', 'issue', 'fail', 'bug',
]


def _extract_troubleshoot(sentences: list[str]) -> list[dict]:
    """문제 해결 단계를 추출합니다."""
    groups = []
    current_problem = None
    current_steps = []

    for s in sentences:
        if _is_problem_description(s):
            # 이전 그룹 저장
            if current_problem and current_steps:
                groups.append({
                    "problem": current_problem,
                    "steps": list(current_steps),
                })
            current_problem = s
            current_steps = []
        elif _is_step_instruction(s) and current_problem:
            current_steps.append(s)

    # 마지막 그룹 저장
    if current_problem and current_steps:
        groups.append({
            "problem": current_problem,
            "steps": list(current_steps),
        })

    # 그룹이 없으면 절차형 문장만 추출
    if not groups:
        steps = [s for s in sentences if _is_step_instruction(s)]
        if steps:
            groups.append({
                "problem": "일반 절차",
                "steps": steps[:10],
            })

    return groups


def _is_problem_description(sentence: str) -> bool:
    """문장이 문제 설명인지 판별합니다."""
    return any(kw in sentence for kw in _PROBLEM_KEYWORDS)


def _is_step_instruction(sentence: str) -> bool:
    """문장이 단계적 지시인지 판별합니다."""
    return any(kw in sentence for kw in _STEP_KEYWORDS)


# ── 퀵 레퍼런스 카드 ──

def _build_quick_reference(sentences: list[str]) -> str:
    """핵심 정보를 요약한 퀵 레퍼런스 카드를 생성합니다."""
    # 핵심 문장 선별: 절차/정보 포함 문장
    key_sentences = []
    for s in sentences:
        if _is_step_instruction(s) or _contains_actionable_info(s):
            if len(s) >= 10:
                key_sentences.append(s)

    if not key_sentences:
        # 상위 5개 긴 문장 사용
        sorted_by_len = sorted(sentences, key=len, reverse=True)
        key_sentences = sorted_by_len[:5]

    # 최대 8개 항목으로 카드 구성
    items = key_sentences[:8]

    lines = ["[퀵 레퍼런스 카드]", ""]
    for i, item in enumerate(items, 1):
        # 60자 초과 시 자르기
        display = item if len(item) <= 60 else item[:57] + "..."
        lines.append(f"  {i}. {display}")

    return "\n".join(lines)


# ── 교육 아웃라인 ──

_SECTION_MARKERS = [
    '소개', '개요', '시작', '기본', '설정', '설치',
    '사용', '활용', '고급', '심화', '문제', '해결',
    '정리', '요약', '마무리', '결론',
    'intro', 'setup', 'usage', 'advanced', 'troubleshoot', 'summary',
]


def _build_training_outline(sentences: list[str]) -> list[str]:
    """자막에서 교육 아웃라인을 생성합니다."""
    outline = []
    seen_markers = set()

    # 1차: 섹션 마커가 포함된 문장에서 주제 추출
    for s in sentences:
        for marker in _SECTION_MARKERS:
            if marker in s and marker not in seen_markers:
                topic = _extract_sentence_topic(s) or s[:20]
                outline.append(f"{topic} ({marker})")
                seen_markers.add(marker)
                break

    # 2차: 마커가 부족하면 일정 간격으로 문장을 샘플링
    if len(outline) < 3 and len(sentences) >= 3:
        step = max(1, len(sentences) // 5)
        for i in range(0, len(sentences), step):
            if len(outline) >= 8:
                break
            topic = _extract_sentence_topic(sentences[i])
            if topic:
                label = f"섹션 {len(outline) + 1}: {topic}"
                if label not in outline:
                    outline.append(label)

    # 최소 구조: 도입/본론/마무리
    if len(outline) < 3:
        defaults = ["도입: 주제 소개", "본론: 핵심 내용", "마무리: 요약 및 정리"]
        for d in defaults:
            if d not in outline:
                outline.append(d)

    return outline
