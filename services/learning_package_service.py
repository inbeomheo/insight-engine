"""학습 패키지 생성 서비스 — 콘텐츠에서 체계적 학습 자료 구성"""
import re
from dataclasses import dataclass, field


@dataclass
class Module:
    """학습 모듈"""
    title: str
    content: str
    key_concepts: list  # list[str]
    exercises: list  # list[str]


@dataclass
class LearningPackage:
    """학습 패키지"""
    title: str
    objectives: list  # list[str]
    modules: list  # list[Module]
    quiz: list  # list[dict]  {question, options, answer}
    estimated_hours: float


# 난이도별 설정
_DIFFICULTY_CONFIG = {
    "beginner": {
        "max_concepts_per_module": 3,
        "exercise_depth": "기초 확인",
        "quiz_count": 3,
        "hours_multiplier": 1.5,  # 입문자는 더 오래 걸림
    },
    "intermediate": {
        "max_concepts_per_module": 5,
        "exercise_depth": "응용 실습",
        "quiz_count": 5,
        "hours_multiplier": 1.0,
    },
    "advanced": {
        "max_concepts_per_module": 7,
        "exercise_depth": "심화 프로젝트",
        "quiz_count": 7,
        "hours_multiplier": 0.8,  # 숙련자는 빠르게 진행
    },
}

_VALID_DIFFICULTIES = set(_DIFFICULTY_CONFIG.keys())


def _extract_key_sentences(text: str) -> list[str]:
    """텍스트에서 핵심 문장을 추출한다."""
    sentences = re.split(r'[.!?。\n]', text)
    key_sentences = []
    for s in sentences:
        s = s.strip()
        if len(s) < 10:
            continue
        # 정의/설명 패턴 우선
        if any(kw in s for kw in ["란 ", "이란 ", "는 ", "이다", "means", "is a", "refers to"]):
            key_sentences.insert(0, s)
        elif len(s) > 20:
            key_sentences.append(s)
    return key_sentences


def _split_into_topics(content: str) -> list[tuple[str, str]]:
    """콘텐츠를 주제별로 분리한다. (제목, 내용) 튜플 리스트."""
    # 마크다운 헤딩 패턴
    heading_pattern = re.compile(r'^#{1,3}\s+(.+)', re.MULTILINE)
    matches = list(heading_pattern.finditer(content))

    if matches:
        topics = []
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            body = content[start:end].strip()
            if body:
                topics.append((title, body))
        return topics if topics else [("주요 내용", content)]

    # 헤딩이 없으면 문단 기준 분할
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    if len(paragraphs) <= 1:
        return [("주요 내용", content)]

    topics = []
    chunk_size = max(1, len(paragraphs) // 3)
    for i in range(0, len(paragraphs), chunk_size):
        chunk = paragraphs[i:i + chunk_size]
        combined = "\n\n".join(chunk)
        # 첫 줄에서 제목 추출
        first_line = chunk[0].split("\n")[0][:40]
        topics.append((first_line, combined))

    return topics


def _generate_concepts(text: str, max_count: int) -> list[str]:
    """텍스트에서 핵심 개념을 추출한다."""
    key_sentences = _extract_key_sentences(text)
    concepts = []
    for s in key_sentences[:max_count]:
        # 문장을 개념 형태로 정리
        concept = s.strip()
        if len(concept) > 60:
            concept = concept[:57] + "..."
        concepts.append(concept)
    return concepts if concepts else ["핵심 내용 학습"]


def _generate_exercises(topic_title: str, depth: str) -> list[str]:
    """주제별 연습 문제를 생성한다."""
    return [
        f"[{depth}] {topic_title}의 핵심 개념을 자신의 말로 정리하세요.",
        f"[{depth}] {topic_title} 관련 실제 사례를 하나 찾아 분석하세요.",
    ]


def _generate_quiz(modules: list[Module], count: int) -> list[dict]:
    """모듈 내용으로 퀴즈를 생성한다."""
    quiz = []
    for i, module in enumerate(modules):
        if len(quiz) >= count:
            break
        concepts = module.key_concepts
        if not concepts:
            continue

        quiz.append({
            "question": f"'{module.title}'에서 다루는 핵심 개념은 무엇입니까?",
            "options": [
                concepts[0] if concepts else "개념 A",
                "관련 없는 개념",
                "다른 주제의 개념",
                "위 모두 해당 없음",
            ],
            "answer": 0,
        })

    # 퀴즈 수가 부족하면 일반 문제 추가
    while len(quiz) < count and modules:
        idx = len(quiz) % len(modules)
        quiz.append({
            "question": f"모듈 '{modules[idx].title}'의 학습 목표를 설명하세요.",
            "options": ["서술형 문제"],
            "answer": 0,
        })

    return quiz[:count]


def _estimate_hours(total_words: int, module_count: int, multiplier: float) -> float:
    """학습 예상 시간을 계산한다."""
    # 읽기: 200 단어/분, 실습: 모듈당 15분
    reading_hours = total_words / 200 / 60
    practice_hours = module_count * 15 / 60
    total = (reading_hours + practice_hours) * multiplier
    return round(max(0.5, total), 1)


def build_learning_pack(content: str, difficulty: str = "intermediate") -> LearningPackage:
    """콘텐츠에서 학습 패키지를 구성한다.

    Args:
        content: 학습 대상 콘텐츠 텍스트
        difficulty: beginner, intermediate, advanced

    Returns:
        LearningPackage 구조
    """
    if not content or not content.strip():
        return LearningPackage(
            title="빈 학습 패키지",
            objectives=[],
            modules=[],
            quiz=[],
            estimated_hours=0.0,
        )

    # 유효하지 않은 난이도는 intermediate 폴백
    if difficulty not in _VALID_DIFFICULTIES:
        difficulty = "intermediate"

    config = _DIFFICULTY_CONFIG[difficulty]
    topics = _split_into_topics(content)

    # 학습 목표 생성
    objectives = [f"'{title}' 주제를 이해하고 설명할 수 있다" for title, _ in topics[:5]]

    # 모듈 생성
    modules = []
    total_words = 0
    for title, body in topics:
        concepts = _generate_concepts(body, config["max_concepts_per_module"])
        exercises = _generate_exercises(title, config["exercise_depth"])
        word_count = len(body.split())
        total_words += word_count

        modules.append(Module(
            title=title,
            content=body,
            key_concepts=concepts,
            exercises=exercises,
        ))

    # 퀴즈 생성
    quiz = _generate_quiz(modules, config["quiz_count"])

    # 학습 시간 추정
    hours = _estimate_hours(total_words, len(modules), config["hours_multiplier"])

    # 패키지 제목
    if topics:
        title = f"{topics[0][0]} 학습 패키지 ({difficulty})"
    else:
        title = f"학습 패키지 ({difficulty})"

    return LearningPackage(
        title=title,
        objectives=objectives,
        modules=modules,
        quiz=quiz,
        estimated_hours=hours,
    )
