"""
퀴즈 생성 서비스 — 콘텐츠에서 자동으로 퀴즈 문항 추출

규칙 기반으로 객관식, T/F, 단답형 문제를 생성합니다.
"""

import logging
import re
import uuid
import hashlib
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

VALID_TYPES = {"multiple_choice", "true_false", "short_answer"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


@dataclass
class QuizQuestion:
    """퀴즈 문항"""
    question_id: str
    question_text: str
    question_type: str  # multiple_choice / true_false / short_answer
    options: list = field(default_factory=list)     # list[str]
    correct_answer: str = ""
    explanation: str = ""
    difficulty: str = "medium"  # easy / medium / hard


@dataclass
class Quiz:
    """퀴즈"""
    quiz_id: str
    title: str
    questions: list = field(default_factory=list)  # list[QuizQuestion]
    passing_score: float = 0.7


def _new_id(prefix: str = "q") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _strip_markdown(text: str) -> str:
    """마크다운 문법 제거"""
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()


def _extract_sentences(content: str) -> list:
    """콘텐츠에서 유효 문장 추출"""
    clean = _strip_markdown(content)
    raw = re.split(r'[.!?。]\s*|\n+', clean)
    sentences = []
    for s in raw:
        s = s.strip()
        if len(s) > 10:
            sentences.append(s)
    return sentences


def _extract_keywords(sentence: str) -> list:
    """문장에서 키워드 추출 (3글자 이상 단어)"""
    return re.findall(r'[가-힣a-zA-Z]{3,}', sentence)


def _make_multiple_choice(sentence: str, keywords: list, difficulty: str) -> QuizQuestion:
    """객관식 문항 생성"""
    if not keywords:
        return _make_true_false(sentence, difficulty)

    target = max(keywords, key=len)
    question_text = sentence.replace(target, "______", 1)

    wrong_options = [kw for kw in keywords if kw != target][:3]
    while len(wrong_options) < 3:
        suffix = f"_{len(wrong_options)}"
        wrong_options.append(f"{target}{suffix}")

    options = [target] + wrong_options
    options.sort(key=lambda x: hashlib.md5(x.encode()).hexdigest())

    return QuizQuestion(
        question_id=_new_id(),
        question_text=f"다음 빈칸에 알맞은 것은? {question_text}",
        question_type="multiple_choice",
        options=options,
        correct_answer=target,
        explanation=f"원문: {sentence}",
        difficulty=difficulty,
    )


def _make_true_false(sentence: str, difficulty: str) -> QuizQuestion:
    """T/F 문항 생성"""
    return QuizQuestion(
        question_id=_new_id(),
        question_text=f"다음 문장이 맞으면 O, 틀리면 X: {sentence}",
        question_type="true_false",
        options=["O", "X"],
        correct_answer="O",
        explanation="원문 그대로이므로 참입니다.",
        difficulty=difficulty,
    )


def _make_short_answer(sentence: str, keywords: list, difficulty: str) -> QuizQuestion:
    """단답형 문항 생성"""
    if not keywords:
        target = sentence.split()[0] if sentence.split() else ""
    else:
        target = keywords[0]

    question_text = sentence.replace(target, "______", 1)

    return QuizQuestion(
        question_id=_new_id(),
        question_text=f"빈칸을 채우세요: {question_text}",
        question_type="short_answer",
        options=[],
        correct_answer=target,
        explanation=f"원문: {sentence}",
        difficulty=difficulty,
    )


def generate_quiz(
    content: str,
    num_questions: int = 5,
    difficulty: str = "medium",
) -> Quiz:
    """콘텐츠 기반 퀴즈 생성

    Args:
        content: 콘텐츠 텍스트
        num_questions: 생성할 문항 수
        difficulty: 난이도 (easy/medium/hard)

    Returns:
        Quiz: 생성된 퀴즈
    """
    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(f"유효하지 않은 난이도: {difficulty}")
    if num_questions < 1:
        raise ValueError("문항 수는 1 이상이어야 합니다.")

    try:
        sentences = _extract_sentences(content)
        if not sentences:
            return Quiz(
                quiz_id=_new_id("quiz"),
                title="퀴즈",
                questions=[],
                passing_score=0.7,
            )

        questions = []
        type_cycle = ["multiple_choice", "true_false", "short_answer"]

        for i in range(min(num_questions, len(sentences))):
            sentence = sentences[i % len(sentences)]
            keywords = _extract_keywords(sentence)
            q_type = type_cycle[i % len(type_cycle)]

            if q_type == "multiple_choice":
                q = _make_multiple_choice(sentence, keywords, difficulty)
            elif q_type == "true_false":
                q = _make_true_false(sentence, difficulty)
            else:
                q = _make_short_answer(sentence, keywords, difficulty)

            questions.append(q)

        passing = {"easy": 0.6, "medium": 0.7, "hard": 0.8}.get(difficulty, 0.7)

        return Quiz(
            quiz_id=_new_id("quiz"),
            title=f"자동 생성 퀴즈 ({difficulty})",
            questions=questions,
            passing_score=passing,
        )
    except Exception as e:
        logger.error(f"퀴즈 생성 처리 실패: {e}")
        raise
def grade_answer(question: QuizQuestion, user_answer: str) -> dict:
    """답안 채점

    Args:
        question: 퀴즈 문항
        user_answer: 사용자 답안

    Returns:
        dict: {correct, score, correct_answer, explanation}
    """
    normalized_user = user_answer.strip().lower()
    normalized_correct = question.correct_answer.strip().lower()

    is_correct = normalized_user == normalized_correct

    score = 1.0 if is_correct else 0.0
    # 단답형은 부분 점수 허용 (정답 포함 시 0.5점)
    if not is_correct and question.question_type == "short_answer":
        if normalized_correct in normalized_user or normalized_user in normalized_correct:
            score = 0.5

    return {
        "correct": is_correct,
        "score": score,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
    }


def shuffle_quiz(quiz: Quiz, seed: int = 0) -> Quiz:
    """퀴즈 문항 순서와 객관식 선택지 순서를 셔플합니다.

    결정적 셔플을 위해 seed를 지정할 수 있습니다.

    Args:
        quiz: 원본 퀴즈
        seed: 랜덤 시드 (기본 0 = 현재 시간 기반)

    Returns:
        셔플된 새 Quiz 객체
    """
    import random
    rng = random.Random(seed if seed != 0 else None)

    shuffled_questions = list(quiz.questions)
    rng.shuffle(shuffled_questions)

    # 객관식 선택지도 셔플
    new_questions = []
    for q in shuffled_questions:
        if q.question_type == 'multiple_choice' and q.options:
            shuffled_options = list(q.options)
            rng.shuffle(shuffled_options)
            new_questions.append(QuizQuestion(
                question_id=q.question_id,
                question_text=q.question_text,
                question_type=q.question_type,
                options=shuffled_options,
                correct_answer=q.correct_answer,
                explanation=q.explanation,
                difficulty=q.difficulty,
            ))
        else:
            new_questions.append(q)

    return Quiz(
        quiz_id=quiz.quiz_id,
        title=quiz.title,
        questions=new_questions,
        passing_score=quiz.passing_score,
    )


def generate_mixed_difficulty_quiz(
    content: str,
    num_questions: int = 6,
    easy_ratio: float = 0.3,
    medium_ratio: float = 0.5,
    hard_ratio: float = 0.2,
) -> Quiz:
    """난이도 비율을 조절하여 혼합 퀴즈를 생성합니다.

    Args:
        content: 콘텐츠 텍스트
        num_questions: 총 문항 수
        easy_ratio: easy 비율 (기본 0.3)
        medium_ratio: medium 비율 (기본 0.5)
        hard_ratio: hard 비율 (기본 0.2)

    Returns:
        혼합 난이도 Quiz
    """
    if num_questions < 1:
        raise ValueError("문항 수는 1 이상이어야 합니다.")

    # 비율 정규화
    total_ratio = easy_ratio + medium_ratio + hard_ratio
    if total_ratio <= 0:
        easy_ratio, medium_ratio, hard_ratio = 0.3, 0.5, 0.2
        total_ratio = 1.0

    easy_count = max(0, round(num_questions * easy_ratio / total_ratio))
    hard_count = max(0, round(num_questions * hard_ratio / total_ratio))
    medium_count = max(0, num_questions - easy_count - hard_count)

    all_questions = []
    for difficulty, count in [('easy', easy_count), ('medium', medium_count), ('hard', hard_count)]:
        if count > 0:
            sub_quiz = generate_quiz(content, num_questions=count, difficulty=difficulty)
            all_questions.extend(sub_quiz.questions)

    return Quiz(
        quiz_id=_new_id("quiz"),
        title=f"혼합 난이도 퀴즈 ({num_questions}문항)",
        questions=all_questions[:num_questions],
        passing_score=0.7,
    )


def calculate_results(quiz: Quiz, answers: list) -> dict:
    """결과 집계

    Args:
        quiz: 퀴즈
        answers: [{question_id: str, answer: str}]

    Returns:
        dict: {total, correct, score, passed, passing_score, details}
    """
    if not quiz.questions:
        return {
            "total": 0,
            "correct": 0,
            "score": 0.0,
            "passed": False,
            "details": [],
        }

    answer_map = {a["question_id"]: a["answer"] for a in answers}

    total_score = 0.0
    correct_count = 0
    details = []

    for q in quiz.questions:
        user_answer = answer_map.get(q.question_id, "")
        result = grade_answer(q, user_answer)
        total_score += result["score"]
        if result["correct"]:
            correct_count += 1
        details.append({
            "question_id": q.question_id,
            "question_type": q.question_type,
            **result,
        })

    total = len(quiz.questions)
    final_score = total_score / total if total > 0 else 0.0

    return {
        "total": total,
        "correct": correct_count,
        "score": round(final_score, 3),
        "passed": final_score >= quiz.passing_score,
        "passing_score": quiz.passing_score,
        "details": details,
    }
