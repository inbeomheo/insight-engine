"""
질문응답 아바타 서비스 테스트
"""
import pytest
from services.qa_avatar_service import (
    create_qa_avatar,
    QAAvatar,
    _split_sentences,
    _extract_keywords,
    _find_relevant_sentence,
)


class TestSplitSentences:
    """문장 분리 테스트."""

    def test_basic_split(self):
        text = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
        result = _split_sentences(text)
        assert len(result) >= 2

    def test_question_marks(self):
        text = "이것은 무엇인가요? 저것은 어떤 기능을 하나요?"
        result = _split_sentences(text)
        assert len(result) >= 1

    def test_short_sentences_filtered(self):
        """10글자 미만 문장은 제외."""
        text = "짧다. 이 문장은 충분히 길어서 포함됩니다."
        result = _split_sentences(text)
        assert all(len(s) >= 10 for s in result)

    def test_newline_split(self):
        text = "첫 번째 줄의 긴 문장입니다\n두 번째 줄의 긴 문장입니다"
        result = _split_sentences(text)
        assert len(result) >= 2


class TestExtractKeywords:
    """키워드 추출 테스트."""

    def test_frequency_based(self):
        sentences = [
            "인공지능 기술은 빠르게 발전하고 있습니다.",
            "인공지능은 다양한 분야에서 활용됩니다.",
            "인공지능 연구가 활발합니다.",
        ]
        keywords = _extract_keywords(sentences)
        assert "인공지능" in keywords

    def test_stopwords_excluded(self):
        sentences = ["그리고 하지만 또한 따라서 그래서"]
        keywords = _extract_keywords(sentences)
        # 불용어는 제외
        for kw in keywords:
            assert kw not in {"그리고", "하지만", "또한", "따라서", "그래서"}

    def test_max_ten(self):
        sentences = [f"키워드{i} 테스트{i} 샘플{i}" for i in range(20)]
        keywords = _extract_keywords(sentences)
        assert len(keywords) <= 10


class TestFindRelevantSentence:
    """관련 문장 찾기 테스트."""

    def test_finds_longest_match(self):
        sentences = [
            "AI는 좋습니다.",
            "AI 기술은 다양한 분야에서 혁신을 이끌고 있으며 앞으로 더 발전할 것입니다.",
        ]
        result = _find_relevant_sentence("AI", sentences)
        # 더 긴 문장 선택
        assert "다양한" in result

    def test_no_match_returns_none(self):
        sentences = ["사과는 빨갛습니다.", "바나나는 노랗습니다."]
        result = _find_relevant_sentence("포도", sentences)
        assert result is None


class TestCreateQaAvatar:
    """create_qa_avatar 통합 테스트."""

    def test_empty_raises(self):
        """빈 지식 텍스트는 ValueError."""
        with pytest.raises(ValueError, match="필요합니다"):
            create_qa_avatar("")

    def test_whitespace_raises(self):
        with pytest.raises(ValueError):
            create_qa_avatar("   ")

    def test_basic_creation(self):
        """기본 아바타 생성."""
        knowledge = (
            "인공지능은 컴퓨터 과학의 한 분야입니다. "
            "머신러닝은 인공지능의 하위 분야로 데이터에서 학습합니다. "
            "딥러닝은 신경망을 사용하여 복잡한 패턴을 학습합니다. "
            "자연어 처리는 인간의 언어를 이해하는 기술입니다."
        )
        result = create_qa_avatar(knowledge)

        assert isinstance(result, QAAvatar)
        assert result.avatar_id
        assert result.persona == "expert"
        assert len(result.knowledge_base) >= 1
        assert result.confidence_threshold > 0

    def test_custom_persona(self):
        """커스텀 페르소나 적용."""
        result = create_qa_avatar(
            "프로그래밍은 컴퓨터에 명령을 내리는 것입니다. 파이썬은 인기 있는 프로그래밍 언어입니다.",
            persona="teacher"
        )
        assert result.persona == "teacher"
        assert result.confidence_threshold == 0.75

    def test_invalid_persona_defaults_expert(self):
        """잘못된 페르소나는 expert로 기본."""
        result = create_qa_avatar(
            "테스트 지식 문장이 여기에 들어갑니다.",
            persona="invalid_persona"
        )
        assert result.persona == "expert"

    def test_sample_qa_generated(self):
        """샘플 QA가 생성됨."""
        knowledge = (
            "블록체인은 분산 원장 기술입니다. 블록체인은 투명성을 보장합니다. "
            "스마트 컨트랙트는 블록체인 위에서 실행되는 자동화 계약입니다. "
            "블록체인 기술은 금융, 물류, 의료 등 다양한 산업에서 활용됩니다."
        )
        result = create_qa_avatar(knowledge)

        assert len(result.sample_qa) >= 1
        for qa in result.sample_qa:
            assert "question" in qa
            assert "answer" in qa
            assert "confidence" in qa

    def test_knowledge_base_from_sentences(self):
        """지식 베이스가 문장 단위로 구성됨."""
        knowledge = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
        result = create_qa_avatar(knowledge)

        assert len(result.knowledge_base) >= 2

    def test_confidence_in_range(self):
        """QA 신뢰도가 0~1 범위."""
        knowledge = (
            "데이터 분석은 의사결정을 돕는 과정입니다. "
            "데이터 분석에는 통계학적 방법이 사용됩니다. "
            "데이터 시각화는 분석 결과를 이해하기 쉽게 표현합니다."
        )
        result = create_qa_avatar(knowledge)

        for qa in result.sample_qa:
            assert 0.0 <= qa["confidence"] <= 1.0

    def test_friendly_persona(self):
        """friendly 페르소나 설정."""
        result = create_qa_avatar(
            "요리는 재미있는 활동입니다. 다양한 재료로 맛있는 음식을 만들 수 있습니다.",
            persona="friendly"
        )
        assert result.persona == "friendly"
        assert result.confidence_threshold == 0.6
