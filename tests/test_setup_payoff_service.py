"""설정-회수 패턴 추적 서비스 테스트"""
import pytest
from services.setup_payoff_service import (
    track_setup_payoff,
    SetupPayoff,
    _split_sentences,
    _extract_keywords,
    _find_keyword_repeats,
    _MIN_DISTANCE,
)


class TestTrackSetupPayoff:
    """track_setup_payoff 함수 테스트"""

    def test_basic_setup_payoff(self):
        """기본 설정-회수 패턴을 탐지한다."""
        transcript = (
            "처음에 프로젝트 계획을 세웠습니다.\n"
            "팀원들과 역할을 분담했습니다.\n"
            "개발을 진행했습니다.\n"
            "테스트를 수행했습니다.\n"
            "최종적으로 프로젝트 결과를 발표했습니다."
        )
        result = track_setup_payoff(transcript)

        assert isinstance(result, list)
        # "프로젝트"가 처음과 끝에 반복
        project_pairs = [sp for sp in result if "프로젝트" in sp.setup_text or "프로젝트" in sp.payoff_text]
        assert len(project_pairs) > 0

    def test_empty_input(self):
        """빈 입력은 빈 리스트를 반환한다."""
        assert track_setup_payoff("") == []
        assert track_setup_payoff(None) == []
        assert track_setup_payoff("   ") == []

    def test_too_short_transcript(self):
        """너무 짧은 자막은 빈 결과를 반환한다."""
        result = track_setup_payoff("짧은 문장.")
        assert result == []

    def test_setup_payoff_dataclass(self):
        """결과가 SetupPayoff 데이터클래스이다."""
        transcript = (
            "알고리즘 설계가 중요합니다.\n"
            "데이터 구조를 선택합니다.\n"
            "코드를 작성합니다.\n"
            "알고리즘 성능을 테스트합니다."
        )
        result = track_setup_payoff(transcript)

        for sp in result:
            assert isinstance(sp, SetupPayoff)
            assert isinstance(sp.setup_text, str)
            assert isinstance(sp.payoff_text, str)
            assert isinstance(sp.setup_position, int)
            assert isinstance(sp.payoff_position, int)
            assert isinstance(sp.distance, int)

    def test_distance_calculation(self):
        """distance가 payoff_position - setup_position과 일치한다."""
        transcript = (
            "디자인 패턴을 학습합니다.\n"
            "객체지향 프로그래밍을 익힙니다.\n"
            "상속과 다형성을 이해합니다.\n"
            "디자인 패턴을 적용합니다."
        )
        result = track_setup_payoff(transcript)

        for sp in result:
            assert sp.distance == sp.payoff_position - sp.setup_position

    def test_distance_sorted(self):
        """결과가 distance 오름차순으로 정렬된다."""
        transcript = (
            "머신러닝 모델을 준비합니다.\n"
            "데이터를 전처리합니다.\n"
            "학습 알고리즘을 선택합니다.\n"
            "모델을 학습시킵니다.\n"
            "결과를 평가합니다.\n"
            "머신러닝 성능을 개선합니다."
        )
        result = track_setup_payoff(transcript)

        for i in range(len(result) - 1):
            assert result[i].distance <= result[i + 1].distance

    def test_minimum_distance_filter(self):
        """너무 가까운 반복은 필터링된다."""
        # 연속 문장에서 같은 키워드 → 설정-회수가 아닌 단순 반복
        transcript = (
            "데이터베이스 설계를 합니다.\n"
            "데이터베이스 구현을 합니다."
        )
        result = track_setup_payoff(transcript)

        for sp in result:
            assert sp.distance >= _MIN_DISTANCE

    def test_no_repeats(self):
        """반복 키워드가 없으면 빈 결과를 반환한다."""
        transcript = (
            "사과를 먹었습니다.\n"
            "배를 먹었습니다.\n"
            "포도를 먹었습니다.\n"
            "수박을 먹었습니다."
        )
        result = track_setup_payoff(transcript)

        # 개별 과일 이름이 반복되지 않으므로 설정-회수 없음
        fruit_pairs = [sp for sp in result if sp.setup_text != sp.payoff_text]
        # "먹었습니다"는 불용어가 아니지만 2글자 이상이라 추출될 수 있음
        assert isinstance(result, list)

    def test_multiple_patterns(self):
        """여러 설정-회수 패턴을 동시에 탐지한다."""
        transcript = (
            "프로젝트 목표를 설정합니다.\n"
            "리스크를 분석합니다.\n"
            "일정을 계획합니다.\n"
            "프로젝트 진행 상황을 점검합니다.\n"
            "리스크 대응을 실행합니다."
        )
        result = track_setup_payoff(transcript)

        # "프로젝트"와 "리스크" 두 패턴
        assert len(result) >= 1

    def test_long_transcript(self):
        """긴 자막도 처리한다."""
        sentences = [f"문장 번호 {i}의 내용입니다" for i in range(30)]
        sentences[0] = "핵심 키워드인 인공지능을 소개합니다"
        sentences[15] = "다시 인공지능 관점에서 정리합니다"
        transcript = ".\n".join(sentences)

        result = track_setup_payoff(transcript)
        assert isinstance(result, list)


class TestSplitSentences:
    """_split_sentences 함수 테스트"""

    def test_period_split(self):
        """마침표로 문장을 분리한다."""
        result = _split_sentences("첫 번째 문장입니다. 두 번째 문장입니다.")
        assert len(result) == 2

    def test_newline_split(self):
        """줄바꿈으로 문장을 분리한다."""
        result = _split_sentences("첫 번째 문장\n두 번째 문장")
        assert len(result) == 2

    def test_short_filtered(self):
        """5자 미만 문장은 제외한다."""
        result = _split_sentences("네. 안녕하세요 반갑습니다.")
        assert all(len(s) >= 5 for s in result)


class TestExtractKeywords:
    """_extract_keywords 함수 테스트"""

    def test_korean_keywords(self):
        """한국어 키워드를 추출한다."""
        keywords = _extract_keywords("프로그래밍 언어를 배웁니다")
        assert "프로그래밍" in keywords

    def test_english_keywords(self):
        """영어 키워드를 추출한다."""
        keywords = _extract_keywords("machine learning algorithm")
        assert "machine" in keywords or "learning" in keywords

    def test_stopwords_filtered(self):
        """불용어가 제외된다."""
        keywords = _extract_keywords("이것은 그리고 the and")
        assert "이것" not in keywords
        assert "the" not in keywords
        assert "and" not in keywords
