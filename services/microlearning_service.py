"""
마이크로러닝 서비스.

콘텐츠를 짧은 학습 단위(마이크로 레슨)로 분할한다.
"""

from dataclasses import dataclass, field
import uuid
import math


@dataclass
class MicroLesson:
    """마이크로 레슨"""
    lesson_id: str = ""
    title: str = ""
    content: str = ""
    duration_min: float = 0.0
    learning_objective: str = ""
    quiz_question: str = None
    order: int = 0


@dataclass
class MicroCourse:
    """마이크로 코스"""
    course_id: str = ""
    title: str = ""
    lessons: list = field(default_factory=list)
    total_duration: float = 0.0


def _estimate_reading_time(text: str) -> float:
    """읽기 시간 추정 (분). 한국어 기준 분당 ~500자"""
    char_count = len(text.replace(" ", "").replace("\n", ""))
    return max(0.5, char_count / 500)


def split_into_lessons(
    content: str,
    max_duration_min: float = 5.0
) -> MicroCourse:
    """
    콘텐츠를 마이크로 레슨으로 분할.

    단락(빈 줄) 기준으로 분할하며, max_duration_min 초과 시 추가 분할한다.
    """
    if not content.strip():
        return MicroCourse(
            course_id=str(uuid.uuid4()),
            title="빈 코스",
            lessons=[],
            total_duration=0.0,
        )

    # 단락 분할 (빈 줄 기준)
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

    lessons = []
    current_chunk = []
    current_duration = 0.0
    lesson_order = 1

    for para in paragraphs:
        para_duration = _estimate_reading_time(para)

        if current_duration + para_duration > max_duration_min and current_chunk:
            # 현재 청크를 레슨으로 생성
            lesson_content = "\n\n".join(current_chunk)
            lessons.append(MicroLesson(
                lesson_id=str(uuid.uuid4()),
                title=f"레슨 {lesson_order}",
                content=lesson_content,
                duration_min=round(current_duration, 2),
                learning_objective=f"레슨 {lesson_order}의 핵심 내용 이해",
                order=lesson_order,
            ))
            lesson_order += 1
            current_chunk = []
            current_duration = 0.0

        current_chunk.append(para)
        current_duration += para_duration

    # 남은 청크 처리
    if current_chunk:
        lesson_content = "\n\n".join(current_chunk)
        lessons.append(MicroLesson(
            lesson_id=str(uuid.uuid4()),
            title=f"레슨 {lesson_order}",
            content=lesson_content,
            duration_min=round(current_duration, 2),
            learning_objective=f"레슨 {lesson_order}의 핵심 내용 이해",
            order=lesson_order,
        ))

    total_duration = sum(l.duration_min for l in lessons)

    return MicroCourse(
        course_id=str(uuid.uuid4()),
        title="마이크로 코스",
        lessons=lessons,
        total_duration=round(total_duration, 2),
    )


def add_quiz(lesson: MicroLesson, question: str) -> MicroLesson:
    """레슨에 퀴즈 추가"""
    return MicroLesson(
        lesson_id=lesson.lesson_id,
        title=lesson.title,
        content=lesson.content,
        duration_min=lesson.duration_min,
        learning_objective=lesson.learning_objective,
        quiz_question=question,
        order=lesson.order,
    )


def reorder_lessons(course: MicroCourse, lesson_ids: list) -> MicroCourse:
    """레슨 순서 변경"""
    lesson_map = {l.lesson_id: l for l in course.lessons}

    reordered = []
    for i, lid in enumerate(lesson_ids, 1):
        if lid in lesson_map:
            lesson = lesson_map[lid]
            reordered.append(MicroLesson(
                lesson_id=lesson.lesson_id,
                title=lesson.title,
                content=lesson.content,
                duration_min=lesson.duration_min,
                learning_objective=lesson.learning_objective,
                quiz_question=lesson.quiz_question,
                order=i,
            ))

    # lesson_ids에 없는 레슨은 뒤에 추가
    remaining_ids = set(lesson_map.keys()) - set(lesson_ids)
    for lid in remaining_ids:
        lesson = lesson_map[lid]
        reordered.append(MicroLesson(
            lesson_id=lesson.lesson_id,
            title=lesson.title,
            content=lesson.content,
            duration_min=lesson.duration_min,
            learning_objective=lesson.learning_objective,
            quiz_question=lesson.quiz_question,
            order=len(reordered) + 1,
        ))

    return MicroCourse(
        course_id=course.course_id,
        title=course.title,
        lessons=reordered,
        total_duration=course.total_duration,
    )


def estimate_completion(course: MicroCourse, speed_factor: float = 1.0) -> float:
    """
    완료 예상 시간.

    speed_factor: 1.0이 기본, 2.0이면 2배속.
    """
    if speed_factor <= 0:
        speed_factor = 1.0

    return round(course.total_duration / speed_factor, 2)
