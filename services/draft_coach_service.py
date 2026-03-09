"""
초안 라이브 코치 서비스

작성 중인 초안에 대해 실시간 피드백을 제공하고,
이전 초안 대비 개선점을 즉시 설명합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class CoachFeedback:
    """코치 피드백 결과."""
    # [{"area": "구조"|"가독성"|"키워드"|"톤", "suggestion": "...", "priority": "high"|"medium"|"low"}]
    improvements: List[Dict] = field(default_factory=list)
    score_delta: float = 0.0       # 이전 대비 점수 변화
    overall_score: float = 0.0     # 현재 점수 (0~100)
    summary: str = ''              # 한줄 요약


# ── 상수 ──────────────────────────────────────────

# 금지 표현 (과장된 수식어)
_FORBIDDEN_WORDS = [
    '놀라운', '혁신적', '획기적', '최고의', '게임체인저',
    '압도적', '경이로운', '드디어', '탁월한', '인상적',
    '뛰어난', '강력한',
]
_FORBIDDEN_RE = re.compile('|'.join(re.escape(w) for w in _FORBIDDEN_WORDS))

# 전환어 패턴
_TRANSITION_RE = re.compile(
    r'(?:따라서|그래서|그러므로|이처럼|또한|게다가|더불어|'
    r'반면|하지만|그러나|예를\s*들어|구체적으로|특히|즉|'
    r'Therefore|Thus|However|Moreover|Furthermore|For\s+example)',
    re.IGNORECASE
)

# 문장 분리
_SENTENCE_SPLIT = re.compile(r'[.!?。]\s*')

# 한국어 단어
_KO_WORD = re.compile(r'[가-힣]+')

# 영어 단어
_EN_WORD = re.compile(r'[a-zA-Z]+')

# 제목 패턴 (마크다운 헤딩)
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 문단 분리
_PARA_SPLIT = re.compile(r'\n\s*\n')


def _split_sentences(text: str) -> List[str]:
    """텍스트를 문장 단위로 분리합니다."""
    parts = _SENTENCE_SPLIT.split(text)
    return [s.strip() for s in parts if s.strip() and len(s.strip()) >= 5]


def _split_paragraphs(text: str) -> List[str]:
    """텍스트를 문단 단위로 분리합니다."""
    parts = _PARA_SPLIT.split(text)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) >= 10]


def _count_words(text: str) -> int:
    """한국어 + 영어 단어 수를 셉니다."""
    ko = _KO_WORD.findall(text)
    en = _EN_WORD.findall(text)
    return len(ko) + len(en)


# ── 구조 분석 ────────────────────────────────────

def _analyze_structure(text: str) -> List[Dict]:
    """구조 측면의 개선 피드백을 반환합니다."""
    suggestions = []
    paragraphs = _split_paragraphs(text)
    sentences = _split_sentences(text)
    headings = _HEADING_RE.findall(text)

    # 1. 문단이 너무 적으면 구조 부족
    if len(paragraphs) <= 1 and len(text) > 200:
        suggestions.append({
            'area': '구조',
            'suggestion': '문단 나누기가 부족합니다. 주제별로 문단을 분리하세요.',
            'priority': 'high',
        })

    # 2. 너무 긴 문단 (300자 이상)
    long_paras = [p for p in paragraphs if len(p) > 300]
    if long_paras:
        suggestions.append({
            'area': '구조',
            'suggestion': f'{len(long_paras)}개 문단이 300자를 초과합니다. 짧게 나누면 가독성이 높아집니다.',
            'priority': 'medium',
        })

    # 3. 제목 없이 긴 글
    if not headings and len(text) > 500:
        suggestions.append({
            'area': '구조',
            'suggestion': '제목(헤딩)이 없습니다. 섹션별 제목을 추가하세요.',
            'priority': 'high',
        })

    # 4. 문장이 너무 적음 (내용 부족)
    if len(sentences) < 3 and len(text) > 100:
        suggestions.append({
            'area': '구조',
            'suggestion': '문장 수가 부족합니다. 핵심 주장을 뒷받침하는 문장을 추가하세요.',
            'priority': 'medium',
        })

    return suggestions


# ── 가독성 분석 ──────────────────────────────────

def _analyze_readability(text: str) -> List[Dict]:
    """가독성 측면의 개선 피드백을 반환합니다."""
    suggestions = []
    sentences = _split_sentences(text)

    # 1. 긴 문장 비율 (60자 초과)
    long_sentences = [s for s in sentences if len(s) > 60]
    if sentences and len(long_sentences) / len(sentences) > 0.5:
        suggestions.append({
            'area': '가독성',
            'suggestion': f'긴 문장({len(long_sentences)}개)이 과반입니다. 짧은 문장으로 나누면 읽기 쉬워집니다.',
            'priority': 'high',
        })

    # 2. 전환어 부족
    transition_count = len(_TRANSITION_RE.findall(text))
    if len(sentences) >= 5 and transition_count == 0:
        suggestions.append({
            'area': '가독성',
            'suggestion': '전환어가 없습니다. "따라서", "또한", "반면" 등을 추가하면 흐름이 자연스러워집니다.',
            'priority': 'medium',
        })

    # 3. 금지 표현 사용
    forbidden_found = _FORBIDDEN_RE.findall(text)
    if forbidden_found:
        unique_found = list(set(forbidden_found))[:5]
        suggestions.append({
            'area': '톤',
            'suggestion': f'과장 표현 감지: {", ".join(unique_found)}. 구체적 수치나 사실로 대체하세요.',
            'priority': 'high',
        })

    # 4. 반복 문장 시작어
    if len(sentences) >= 4:
        starts = [s[:2] for s in sentences if len(s) >= 2]
        start_counts: Dict[str, int] = {}
        for s in starts:
            start_counts[s] = start_counts.get(s, 0) + 1
        repeated = [k for k, v in start_counts.items() if v >= 3]
        if repeated:
            suggestions.append({
                'area': '가독성',
                'suggestion': f'문장 시작이 반복됩니다("{repeated[0]}..."). 다양한 시작어를 사용하세요.',
                'priority': 'low',
            })

    return suggestions


# ── 점수 계산 ────────────────────────────────────

def _compute_score(text: str) -> float:
    """현재 초안의 종합 점수를 계산합니다 (0~100)."""
    if not text or not text.strip():
        return 0.0

    score = 50.0  # 기본 점수

    paragraphs = _split_paragraphs(text)
    sentences = _split_sentences(text)
    headings = _HEADING_RE.findall(text)
    word_count = _count_words(text)

    # 구조 보너스/감점
    if len(paragraphs) >= 3:
        score += 10.0
    elif len(paragraphs) <= 1 and len(text) > 200:
        score -= 10.0

    # 제목 보너스
    if headings:
        score += min(10.0, len(headings) * 3.0)

    # 적절한 문장 수
    if 5 <= len(sentences) <= 30:
        score += 10.0
    elif len(sentences) > 30:
        score += 5.0

    # 전환어 보너스
    transition_count = len(_TRANSITION_RE.findall(text))
    score += min(10.0, transition_count * 2.0)

    # 금지 표현 감점
    forbidden_count = len(_FORBIDDEN_RE.findall(text))
    score -= min(15.0, forbidden_count * 5.0)

    # 긴 문장 감점
    long_sentences = [s for s in sentences if len(s) > 60]
    if sentences:
        long_ratio = len(long_sentences) / len(sentences)
        score -= long_ratio * 10.0

    # 단어 수 보너스 (200~2000자 적정 범위)
    if 50 <= word_count <= 500:
        score += 5.0
    elif word_count > 500:
        score += 3.0

    # 긴 문단 감점
    long_paras = [p for p in paragraphs if len(p) > 300]
    score -= min(10.0, len(long_paras) * 3.0)

    return round(max(0.0, min(100.0, score)), 1)


# ── diff 기반 개선점 분석 ────────────────────────

def _diff_improvements(current: str, previous: str) -> List[Dict]:
    """이전 초안 대비 개선점을 분석합니다."""
    improvements = []

    cur_sentences = _split_sentences(current)
    prev_sentences = _split_sentences(previous)
    cur_paras = _split_paragraphs(current)
    prev_paras = _split_paragraphs(previous)

    # 문장 수 변화
    sent_diff = len(cur_sentences) - len(prev_sentences)
    if sent_diff > 0:
        improvements.append({
            'area': '구조',
            'suggestion': f'문장이 {sent_diff}개 추가되어 내용이 풍부해졌습니다.',
            'priority': 'low',
        })

    # 문단 수 변화
    para_diff = len(cur_paras) - len(prev_paras)
    if para_diff > 0:
        improvements.append({
            'area': '구조',
            'suggestion': f'문단이 {para_diff}개 추가되어 구조가 개선되었습니다.',
            'priority': 'low',
        })

    # 전환어 변화
    cur_trans = len(_TRANSITION_RE.findall(current))
    prev_trans = len(_TRANSITION_RE.findall(previous))
    if cur_trans > prev_trans:
        improvements.append({
            'area': '가독성',
            'suggestion': f'전환어가 {cur_trans - prev_trans}개 추가되어 흐름이 좋아졌습니다.',
            'priority': 'low',
        })

    # 금지 표현 변화
    cur_forbidden = len(_FORBIDDEN_RE.findall(current))
    prev_forbidden = len(_FORBIDDEN_RE.findall(previous))
    if cur_forbidden < prev_forbidden:
        improvements.append({
            'area': '톤',
            'suggestion': f'과장 표현이 {prev_forbidden - cur_forbidden}개 줄어 톤이 개선되었습니다.',
            'priority': 'low',
        })
    elif cur_forbidden > prev_forbidden:
        improvements.append({
            'area': '톤',
            'suggestion': f'과장 표현이 {cur_forbidden - prev_forbidden}개 늘었습니다. 줄여보세요.',
            'priority': 'medium',
        })

    # 제목 추가 여부
    cur_headings = len(_HEADING_RE.findall(current))
    prev_headings = len(_HEADING_RE.findall(previous))
    if cur_headings > prev_headings:
        improvements.append({
            'area': '구조',
            'suggestion': f'제목이 {cur_headings - prev_headings}개 추가되어 탐색성이 좋아졌습니다.',
            'priority': 'low',
        })

    # 긴 문장 비율 변화
    cur_long = len([s for s in cur_sentences if len(s) > 60])
    prev_long = len([s for s in prev_sentences if len(s) > 60])
    cur_ratio = cur_long / max(1, len(cur_sentences))
    prev_ratio = prev_long / max(1, len(prev_sentences))
    if cur_ratio < prev_ratio - 0.1:
        improvements.append({
            'area': '가독성',
            'suggestion': '긴 문장 비율이 줄어 가독성이 향상되었습니다.',
            'priority': 'low',
        })

    return improvements


# ── 메인 함수 ────────────────────────────────────

def coach_feedback(
    current_draft: str,
    previous_draft: Optional[str] = None
) -> CoachFeedback:
    """현재 초안을 분석하여 개선 피드백을 반환합니다.

    Args:
        current_draft: 현재 초안 텍스트
        previous_draft: 이전 초안 (있으면 diff 기반 비교)

    Returns:
        CoachFeedback dataclass
    """
    if not current_draft or not current_draft.strip():
        return CoachFeedback(
            improvements=[],
            score_delta=0.0,
            overall_score=0.0,
            summary='초안이 비어 있습니다.',
        )

    # 피드백 수집
    improvements = []
    improvements.extend(_analyze_structure(current_draft))
    improvements.extend(_analyze_readability(current_draft))

    # 점수 계산
    current_score = _compute_score(current_draft)
    score_delta = 0.0

    # diff 기반 분석
    if previous_draft and previous_draft.strip():
        previous_score = _compute_score(previous_draft)
        score_delta = round(current_score - previous_score, 1)
        diff_items = _diff_improvements(current_draft, previous_draft)
        improvements.extend(diff_items)

    # 우선순위 정렬 (high > medium > low)
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    improvements.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 2))

    # 요약 생성
    high_count = sum(1 for i in improvements if i.get('priority') == 'high')
    if high_count > 0:
        summary = f'점수 {current_score}점. 중요 개선사항 {high_count}건을 확인하세요.'
    elif improvements:
        summary = f'점수 {current_score}점. {len(improvements)}건의 개선 제안이 있습니다.'
    else:
        summary = f'점수 {current_score}점. 잘 작성된 초안입니다.'

    return CoachFeedback(
        improvements=improvements,
        score_delta=score_delta,
        overall_score=current_score,
        summary=summary,
    )
