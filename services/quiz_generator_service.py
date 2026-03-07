"""
인터랙티브 퀴즈 생성 서비스

콘텐츠에서 핵심 정보를 추출하여 퀴즈/설문을 자동 생성합니다.
규칙 기반으로 객관식, OX, 빈칸 채우기 문제를 생성합니다.
"""
import re
import hashlib
import logging
from typing import List

logger = logging.getLogger(__name__)

# 문장에서 핵심 정보 추출용 패턴
_FACT_PATTERNS = [
    # "X는 Y이다" 패턴
    re.compile(r'([가-힣a-zA-Z0-9\s]{3,20})[은는이가]\s+(.{5,40})[이다입니다]'),
    # 숫자 포함 사실
    re.compile(r'(.{5,30}?)\s*(\d+[%％만억원개건명][\w\s]{0,15})'),
    # "X를 통해 Y" 패턴
    re.compile(r'(.{5,25})[을를]\s*통해\s*(.{5,30})'),
]

# 불용 문장 필터
_SKIP_PATTERNS = [
    re.compile(r'^(참고|주의|출처|이미지|사진|그림)\s*[:：]'),
    re.compile(r'^[-*•]'),
    re.compile(r'^\d+\.\s*$'),
]


def generate_quiz(content: str, count: int = 5) -> dict:
    """콘텐츠에서 퀴즈를 자동 생성합니다.

    Args:
        content: 퀴즈 원본 콘텐츠
        count: 생성할 문제 수 (기본 5, 최대 10)

    Returns:
        {
            "quiz_id": str,
            "title": str,
            "questions": [
                {
                    "id": int,
                    "type": "multiple_choice" | "true_false" | "fill_blank",
                    "question": str,
                    "options": list[str] | None,
                    "answer": str,
                    "explanation": str,
                }
            ],
            "total_questions": int,
        }
    """
    if not content or not content.strip():
        return {
            'quiz_id': '',
            'title': '',
            'questions': [],
            'total_questions': 0,
        }

    count = max(1, min(count, 10))
    plain = _strip_markdown(content)
    sentences = _extract_key_sentences(plain)

    questions = []
    used_sentences = set()

    for sentence in sentences:
        if len(questions) >= count:
            break
        if sentence in used_sentences:
            continue

        q = _create_question(sentence, len(questions) + 1)
        if q:
            questions.append(q)
            used_sentences.add(sentence)

    quiz_id = hashlib.md5(content[:200].encode()).hexdigest()[:8]

    return {
        'quiz_id': quiz_id,
        'title': '콘텐츠 이해도 퀴즈',
        'questions': questions,
        'total_questions': len(questions),
    }


def _strip_markdown(text: str) -> str:
    """마크다운 문법을 제거합니다."""
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


def _extract_key_sentences(text: str) -> List[str]:
    """핵심 문장을 추출합니다."""
    raw_sentences = re.split(r'[.!。]\s*|\n+', text)
    sentences = []

    for s in raw_sentences:
        s = s.strip()
        if len(s) < 15 or len(s) > 150:
            continue
        if any(pat.search(s) for pat in _SKIP_PATTERNS):
            continue
        sentences.append(s)

    return sentences


def _create_question(sentence: str, qid: int) -> dict | None:
    """문장에서 문제를 생성합니다. 3가지 유형을 순환."""
    q_type = ['multiple_choice', 'true_false', 'fill_blank'][qid % 3]

    if q_type == 'true_false':
        return _create_true_false(sentence, qid)
    elif q_type == 'fill_blank':
        return _create_fill_blank(sentence, qid)
    else:
        return _create_multiple_choice(sentence, qid)


def _create_true_false(sentence: str, qid: int) -> dict:
    """OX 문제 생성."""
    return {
        'id': qid,
        'type': 'true_false',
        'question': f'다음 설명이 맞으면 O, 틀리면 X를 선택하세요: "{sentence}"',
        'options': ['O', 'X'],
        'answer': 'O',
        'explanation': f'본문에 따르면 이 설명은 사실입니다.',
    }


def _create_fill_blank(sentence: str, qid: int) -> dict | None:
    """빈칸 채우기 문제 생성."""
    words = re.findall(r'[가-힣a-zA-Z0-9]+', sentence)
    # 3글자 이상 단어 중 가장 긴 것을 빈칸으로
    candidates = [w for w in words if len(w) >= 3]
    if not candidates:
        return _create_true_false(sentence, qid)

    blank_word = max(candidates, key=len)
    blanked = sentence.replace(blank_word, '______', 1)

    return {
        'id': qid,
        'type': 'fill_blank',
        'question': f'다음 빈칸에 들어갈 단어는? "{blanked}"',
        'options': None,
        'answer': blank_word,
        'explanation': f'정답은 "{blank_word}"입니다.',
    }


def _create_multiple_choice(sentence: str, qid: int) -> dict:
    """객관식 문제 생성."""
    # 문장을 질문 형태로 변환
    question_text = f'다음 중 본문의 내용과 일치하는 것은?'

    # 정답 옵션
    correct = sentence if len(sentence) <= 60 else sentence[:57] + '...'

    # 오답 생성 (문장 변형)
    wrong_options = _generate_wrong_options(sentence)

    options = [correct] + wrong_options[:3]
    # 순서 섞기 (결정적: qid 기반)
    import random
    rng = random.Random(qid)
    rng.shuffle(options)

    return {
        'id': qid,
        'type': 'multiple_choice',
        'question': question_text,
        'options': options,
        'answer': correct,
        'explanation': f'본문에 "{correct}" 내용이 있습니다.',
    }


def _generate_wrong_options(sentence: str) -> List[str]:
    """오답 선택지를 생성합니다."""
    wrong = []

    # 부정 변환
    if '있다' in sentence or '있습니다' in sentence:
        wrong.append(sentence.replace('있다', '없다').replace('있습니다', '없습니다'))
    elif '이다' in sentence or '입니다' in sentence:
        wrong.append(sentence.replace('이다', '이 아니다').replace('입니다', '이 아닙니다'))

    # 숫자 변형
    numbers = re.findall(r'\d+', sentence)
    if numbers:
        for num in numbers[:1]:
            n = int(num)
            wrong.append(sentence.replace(num, str(n * 2), 1))
            wrong.append(sentence.replace(num, str(max(1, n // 2)), 1))

    # 기본 오답
    if len(wrong) < 3:
        wrong.append('위의 내용은 본문에 언급되지 않았다')
    if len(wrong) < 3:
        wrong.append('본문에서 정확한 정보를 확인할 수 없다')
    if len(wrong) < 3:
        wrong.append('해당 내용은 본문과 반대되는 설명이다')

    # 길이 제한
    return [w[:60] if len(w) > 60 else w for w in wrong[:3]]
