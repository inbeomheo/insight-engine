"""학습 패키지 생성 서비스 테스트"""
import pytest
from services.learning_package_service import (
    build_learning_pack,
    LearningPackage,
    Module,
    _extract_key_sentences,
    _split_into_topics,
    _VALID_DIFFICULTIES,
)


class TestBuildLearningPack:
    """build_learning_pack 함수 테스트"""

    def test_basic_package_creation(self):
        """기본 콘텐츠로 학습 패키지를 생성한다."""
        content = (
            "## 파이썬 기초\n\n"
            "파이썬은 읽기 쉬운 프로그래밍 언어입니다. "
            "변수, 함수, 클래스 등의 개념을 학습합니다.\n\n"
            "## 자료구조\n\n"
            "리스트, 딕셔너리, 세트 등의 자료구조를 다룹니다."
        )
        result = build_learning_pack(content)

        assert isinstance(result, LearningPackage)
        assert result.title != ""
        assert len(result.modules) > 0
        assert len(result.objectives) > 0
        assert result.estimated_hours > 0

    def test_empty_content(self):
        """빈 콘텐츠는 빈 패키지를 반환한다."""
        result = build_learning_pack("")

        assert result.title == "빈 학습 패키지"
        assert result.modules == []
        assert result.objectives == []
        assert result.quiz == []
        assert result.estimated_hours == 0.0

    def test_none_content(self):
        """None 콘텐츠도 빈 패키지를 반환한다."""
        result = build_learning_pack(None)
        assert result.title == "빈 학습 패키지"

    def test_beginner_difficulty(self):
        """beginner 난이도 설정이 적용된다."""
        content = "## 입문\n\n프로그래밍이란 컴퓨터에 명령을 내리는 것입니다."
        result = build_learning_pack(content, difficulty="beginner")

        assert "beginner" in result.title
        assert len(result.quiz) <= 3  # beginner quiz_count = 3

    def test_advanced_difficulty(self):
        """advanced 난이도 설정이 적용된다."""
        content = "## 고급 과정\n\n메타프로그래밍과 디자인 패턴을 심화 학습합니다."
        result = build_learning_pack(content, difficulty="advanced")

        assert "advanced" in result.title

    def test_invalid_difficulty_fallback(self):
        """잘못된 난이도는 intermediate로 폴백한다."""
        content = "## 학습 내용\n\n기본 개념을 설명합니다."
        result = build_learning_pack(content, difficulty="impossible")

        assert "intermediate" in result.title

    def test_modules_have_content(self):
        """각 모듈에 콘텐츠가 존재한다."""
        content = (
            "## 모듈 A\n\n첫 번째 주제에 대한 상세한 설명입니다.\n\n"
            "## 모듈 B\n\n두 번째 주제에 대한 상세한 설명입니다."
        )
        result = build_learning_pack(content)

        for module in result.modules:
            assert isinstance(module, Module)
            assert module.title != ""
            assert module.content != ""

    def test_modules_have_exercises(self):
        """각 모듈에 연습 문제가 포함된다."""
        content = "## 실습\n\n실습을 통해 개념을 익힙니다."
        result = build_learning_pack(content)

        for module in result.modules:
            assert len(module.exercises) > 0

    def test_modules_have_key_concepts(self):
        """각 모듈에 핵심 개념이 포함된다."""
        content = (
            "## 핵심 개념\n\n"
            "객체지향 프로그래밍이란 데이터와 함수를 묶는 패러다임이다. "
            "캡슐화는 데이터를 보호하는 기법이다."
        )
        result = build_learning_pack(content)

        for module in result.modules:
            assert len(module.key_concepts) > 0

    def test_quiz_generation(self):
        """퀴즈가 생성된다."""
        content = (
            "## 파트 1\n\n변수의 개념을 이해합니다.\n\n"
            "## 파트 2\n\n함수의 정의와 호출을 학습합니다."
        )
        result = build_learning_pack(content)

        assert len(result.quiz) > 0
        for q in result.quiz:
            assert "question" in q
            assert "options" in q
            assert "answer" in q

    def test_estimated_hours_positive(self):
        """학습 시간이 양수로 계산된다."""
        content = "## 학습\n\n" + "이것은 학습 콘텐츠입니다. " * 50
        result = build_learning_pack(content)

        assert result.estimated_hours >= 0.5

    def test_objectives_from_topics(self):
        """학습 목표가 주제에서 파생된다."""
        content = (
            "## 데이터베이스 설계\n\n테이블 구조를 설계합니다.\n\n"
            "## 쿼리 최적화\n\n성능을 개선하는 방법을 배웁니다."
        )
        result = build_learning_pack(content)

        assert len(result.objectives) > 0
        # 목표에 주제명이 반영됨
        objectives_text = " ".join(result.objectives)
        assert "데이터베이스 설계" in objectives_text or "쿼리 최적화" in objectives_text


class TestExtractKeySentences:
    """_extract_key_sentences 함수 테스트"""

    def test_definition_priority(self):
        """정의 문장이 우선 추출된다."""
        text = "파이썬은 프로그래밍 언어이다. 날씨가 좋습니다."
        result = _extract_key_sentences(text)

        assert len(result) > 0
        assert "이다" in result[0] or "언어" in result[0]

    def test_short_sentences_filtered(self):
        """짧은 문장은 제외된다."""
        text = "좋아요. 네. 그래요."
        result = _extract_key_sentences(text)
        assert len(result) == 0


class TestSplitIntoTopics:
    """_split_into_topics 함수 테스트"""

    def test_markdown_headings(self):
        """마크다운 헤딩 기준으로 분할한다."""
        content = "## 주제 1\n내용 A\n## 주제 2\n내용 B"
        result = _split_into_topics(content)

        assert len(result) == 2
        assert result[0][0] == "주제 1"

    def test_no_headings(self):
        """헤딩이 없으면 문단 기준으로 분할한다."""
        content = "첫 번째 내용입니다.\n\n두 번째 내용입니다.\n\n세 번째 내용입니다."
        result = _split_into_topics(content)

        assert len(result) >= 1
