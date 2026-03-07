"""
질문-답변 완결성 검사 서비스

콘텐츠 내 질문형 헤딩이나 문장을 감지하고,
해당 질문 뒤에 직접적인 답변이 존재하는지 검사합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 질문형 헤딩 감지 패턴 (한국어 + 영어)
_HEADING_QUESTION_PATTERNS = [
    # 한국어 질문 어미
    re.compile(r'인가요\s*\??$'),
    re.compile(r'할까요\s*\??$'),
    re.compile(r'인가\s*\??$'),
    re.compile(r'일까\s*\??$'),
    re.compile(r'인지\s*\??$'),
    re.compile(r'는가\s*\??$'),
    re.compile(r'나요\s*\??$'),
    re.compile(r'까요\s*\??$'),
    re.compile(r'\?\s*$'),
    # 영어 질문 패턴
    re.compile(r'^What\s+(is|are|was|were)\b', re.IGNORECASE),
    re.compile(r'^How\s+(to|do|does|can|should)\b', re.IGNORECASE),
    re.compile(r'^Why\s+(is|are|do|does|should)\b', re.IGNORECASE),
    re.compile(r'^When\s+(is|are|do|does|should)\b', re.IGNORECASE),
    re.compile(r'^Where\s+(is|are|do|does|should)\b', re.IGNORECASE),
    re.compile(r'^Who\s+(is|are|was|were)\b', re.IGNORECASE),
    re.compile(r'^Can\s+(I|we|you)\b', re.IGNORECASE),
    re.compile(r'^Is\s+(it|there|this)\b', re.IGNORECASE),
]

# 본문 질문 감지 패턴
_BODY_QUESTION_PATTERNS = [
    re.compile(r'\?\s*$'),
    re.compile(r'할까\s*$'),
    re.compile(r'인가\s*$'),
    re.compile(r'는가\s*$'),
    re.compile(r'일까\s*$'),
    re.compile(r'나요\s*$'),
    re.compile(r'까요\s*$'),
]

# 답변 신호 패턴
_ANSWER_SIGNAL_PATTERNS = [
    # 한국어 서술형 어미
    re.compile(r'입니다'),
    re.compile(r'합니다'),
    re.compile(r'됩니다'),
    re.compile(r'습니다'),
    re.compile(r'이다[.\s]'),
    re.compile(r'된다[.\s]'),
    re.compile(r'한다[.\s]'),
    re.compile(r'있다[.\s]'),
    re.compile(r'이에요'),
    re.compile(r'해요'),
    # 한국어 정의/설명 패턴
    re.compile(r'[은는].*[을를]\s*의미'),
    re.compile(r'[은는].*[을를]\s*뜻'),
    re.compile(r'이란\s'),
    re.compile(r'란\s'),
    # 영어 답변 신호
    re.compile(r'\bThe\s+answer\s+is\b', re.IGNORECASE),
    re.compile(r'^Yes[,.\s]', re.IGNORECASE),
    re.compile(r'^No[,.\s]', re.IGNORECASE),
    re.compile(r'\bmeans\b', re.IGNORECASE),
    re.compile(r'\brefers\s+to\b', re.IGNORECASE),
    re.compile(r'\bis\s+defined\s+as\b', re.IGNORECASE),
    re.compile(r'\bis\s+a\b', re.IGNORECASE),
    # 영어 명령/지시형 답변
    re.compile(r'^Run\b', re.IGNORECASE),
    re.compile(r'^Use\b', re.IGNORECASE),
    re.compile(r'^Install\b', re.IGNORECASE),
    re.compile(r'\bto\s+get\s+started\b', re.IGNORECASE),
    re.compile(r'\byou\s+can\b', re.IGNORECASE),
]

# 마크다운 헤딩 파싱 패턴
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)


def check_qa_closure(content: str) -> dict:
    """콘텐츠 내 질문-답변 완결성을 검사합니다.

    Args:
        content: 분석할 마크다운/텍스트 콘텐츠

    Returns:
        {
            "questions": [{"question": str, "source": str, "has_answer": bool,
                           "answer_excerpt": str, "status": str}],
            "summary": {"total_questions": int, "answered": int, "unanswered": int},
            "closure_score": float,  # 0-100
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'questions': [],
            'summary': {'total_questions': 0, 'answered': 0, 'unanswered': 0},
            'closure_score': 100.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    lines = content.split('\n')
    questions = []

    # 1단계: 헤딩에서 질문 감지
    heading_questions = _detect_heading_questions(lines)
    questions.extend(heading_questions)

    # 2단계: 본문에서 질문 감지
    body_questions = _detect_body_questions(lines)
    questions.extend(body_questions)

    # 중복 제거 (동일 질문 텍스트)
    seen = set()
    unique_questions = []
    for q in questions:
        key = q['question'].strip()
        if key not in seen:
            seen.add(key)
            unique_questions.append(q)
    questions = unique_questions

    # 3단계: 각 질문에 대해 답변 존재 여부 확인
    for q_info in questions:
        _check_answer_exists(q_info, lines)

    # 4단계: 요약 및 점수 계산
    total = len(questions)
    answered = sum(1 for q in questions if q['has_answer'])
    unanswered = total - answered

    closure_score = (answered / total * 100.0) if total > 0 else 100.0
    closure_score = round(closure_score, 1)

    suggestions = _generate_suggestions(questions, total, answered, unanswered)

    return {
        'questions': questions,
        'summary': {
            'total_questions': total,
            'answered': answered,
            'unanswered': unanswered,
        },
        'closure_score': closure_score,
        'suggestions': suggestions,
    }


def _is_question_heading(text: str) -> bool:
    """헤딩 텍스트가 질문형인지 판별합니다."""
    for pattern in _HEADING_QUESTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _is_question_body(text: str) -> bool:
    """본문 문장이 질문형인지 판별합니다."""
    for pattern in _BODY_QUESTION_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _has_answer_signal(text: str) -> bool:
    """텍스트에 답변 신호가 있는지 확인합니다."""
    for pattern in _ANSWER_SIGNAL_PATTERNS:
        if pattern.search(text):
            return True
    return False


def _detect_heading_questions(lines: list) -> list:
    """마크다운 헤딩에서 질문형을 감지합니다."""
    questions = []
    for line_idx, line in enumerate(lines):
        match = _HEADING_RE.match(line.strip())
        if match:
            heading_text = match.group(2).strip()
            if _is_question_heading(heading_text):
                questions.append({
                    'question': heading_text,
                    'source': 'heading',
                    'has_answer': False,
                    'answer_excerpt': '',
                    'status': 'unanswered',
                    '_line_idx': line_idx,
                })
    return questions


def _detect_body_questions(lines: list) -> list:
    """본문 문장에서 질문형을 감지합니다."""
    questions = []
    for line_idx, line in enumerate(lines):
        stripped = line.strip()
        # 헤딩이면 스킵 (이미 처리됨)
        if _HEADING_RE.match(stripped):
            continue
        # 빈 줄 스킵
        if not stripped:
            continue
        # 리스트 아이템 등 짧은 문장은 스킵 (최소 5자)
        if len(stripped) < 5:
            continue
        if _is_question_body(stripped):
            questions.append({
                'question': stripped,
                'source': 'body',
                'has_answer': False,
                'answer_excerpt': '',
                'status': 'unanswered',
                '_line_idx': line_idx,
            })
    return questions


def _check_answer_exists(q_info: dict, lines: list) -> None:
    """질문 뒤 3문장 이내에 답변이 있는지 확인합니다.

    답변이 발견되면 q_info를 직접 수정합니다.
    """
    line_idx = q_info['_line_idx']
    sentences_checked = 0
    answer_excerpt = ''

    # 질문 다음 줄부터 탐색
    for i in range(line_idx + 1, len(lines)):
        current_line = lines[i].strip()

        # 빈 줄은 건너뛰기
        if not current_line:
            continue

        # 다른 헤딩을 만나면 탐색 중단
        if _HEADING_RE.match(current_line):
            break

        # 또 다른 질문이면 미답변으로 판정
        if _is_question_body(current_line):
            break

        sentences_checked += 1

        # 답변 신호 확인
        if _has_answer_signal(current_line):
            q_info['has_answer'] = True
            q_info['status'] = 'answered'
            # 발췌문 생성 (최대 100자)
            excerpt = current_line
            if len(excerpt) > 100:
                excerpt = excerpt[:97] + '...'
            q_info['answer_excerpt'] = excerpt
            break

        # 3문장까지만 확인
        if sentences_checked >= 3:
            break

    # 내부 인덱스 필드 제거
    del q_info['_line_idx']


def _generate_suggestions(questions: list, total: int, answered: int, unanswered: int) -> list:
    """검사 결과에 기반한 개선 제안을 생성합니다."""
    suggestions = []

    if total == 0:
        return suggestions

    if unanswered > 0:
        unanswered_qs = [q['question'] for q in questions if not q['has_answer']]
        suggestions.append(
            f'{unanswered}개의 질문에 답변이 부족합니다. '
            f'각 질문 뒤에 명확한 답변을 추가하세요.'
        )
        # 구체적인 미답변 질문 안내 (최대 3개)
        for q_text in unanswered_qs[:3]:
            display_text = q_text if len(q_text) <= 50 else q_text[:47] + '...'
            suggestions.append(f'미답변 질문: "{display_text}"')

    if answered == total and total > 0:
        suggestions.append('모든 질문에 답변이 제공되어 있습니다.')

    # 연속 질문 경고
    consecutive_count = 0
    max_consecutive = 0
    for q in questions:
        if not q['has_answer']:
            consecutive_count += 1
            max_consecutive = max(max_consecutive, consecutive_count)
        else:
            consecutive_count = 0

    if max_consecutive >= 2:
        suggestions.append(
            f'연속 {max_consecutive}개의 질문이 답변 없이 나열되어 있습니다. '
            f'각 질문 사이에 답변을 삽입하세요.'
        )

    return suggestions
