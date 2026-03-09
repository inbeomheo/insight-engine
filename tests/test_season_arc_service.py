"""시즌 아크 설계 서비스 테스트"""
import pytest
from services.season_arc_service import (
    design_season_arc,
    SeasonArc,
    EpisodePlan,
    _detect_arc_type,
    _assign_roles,
    _generate_season_title,
)


class TestDesignSeasonArc:
    """design_season_arc 함수 테스트"""

    def test_basic_arc_creation(self):
        """기본 에피소드 목록으로 시즌 아크를 생성한다."""
        episodes = [
            {"title": "시작", "theme": "도입"},
            {"title": "전개", "theme": "발전"},
            {"title": "결말", "theme": "마무리"},
        ]
        result = design_season_arc(episodes)

        assert isinstance(result, SeasonArc)
        assert result.total_episodes == 3
        assert len(result.episodes) == 3
        assert result.arc_type in {"rising", "episodic", "mystery", "transformation"}

    def test_empty_episodes(self):
        """빈 에피소드 목록은 빈 시즌을 반환한다."""
        result = design_season_arc([])

        assert result.season_title == "빈 시즌"
        assert result.episodes == []
        assert result.arc_type == "episodic"
        assert result.total_episodes == 0

    def test_single_episode(self):
        """단일 에피소드로 시즌을 생성한다."""
        episodes = [{"title": "단독 에피소드", "theme": "단일 주제"}]
        result = design_season_arc(episodes)

        assert result.total_episodes == 1
        assert len(result.episodes) == 1
        assert result.episodes[0].episode_number == 1
        assert result.episodes[0].title == "단독 에피소드"

    def test_episode_numbering(self):
        """에피소드 번호가 1부터 순차적으로 매겨진다."""
        episodes = [
            {"title": f"에피소드 {i}", "theme": f"주제 {i}"}
            for i in range(5)
        ]
        result = design_season_arc(episodes)

        for i, ep in enumerate(result.episodes):
            assert ep.episode_number == i + 1

    def test_mystery_arc_detection(self):
        """미스터리 키워드가 있으면 mystery 아크를 감지한다."""
        episodes = [
            {"title": "비밀의 시작", "theme": "미스터리"},
            {"title": "단서 추적", "theme": "clue"},
            {"title": "진실 공개", "theme": "reveal"},
        ]
        result = design_season_arc(episodes)
        assert result.arc_type == "mystery"

    def test_transformation_arc_detection(self):
        """변화/성장 키워드가 있으면 transformation 아크를 감지한다."""
        episodes = [
            {"title": "변화의 시작", "theme": "성장"},
            {"title": "도전과 시련", "theme": "변화"},
            {"title": "새로운 나", "theme": "변신"},
        ]
        result = design_season_arc(episodes)
        assert result.arc_type == "transformation"

    def test_episodic_arc_detection(self):
        """독립/옴니버스 키워드가 있으면 episodic 아크를 감지한다."""
        episodes = [
            {"title": "이야기 1", "theme": "독립 에피소드"},
            {"title": "이야기 2", "theme": "옴니버스"},
        ]
        result = design_season_arc(episodes)
        assert result.arc_type == "episodic"

    def test_default_rising_arc(self):
        """특별한 키워드가 없으면 rising 아크를 기본값으로 사용한다."""
        episodes = [
            {"title": "요리법 1", "theme": "파스타"},
            {"title": "요리법 2", "theme": "스테이크"},
        ]
        result = design_season_arc(episodes)
        assert result.arc_type == "rising"

    def test_missing_title_uses_default(self):
        """title이 없는 에피소드는 기본 제목을 사용한다."""
        episodes = [
            {"theme": "주제만 있음"},
            {"title": "제목 있음", "theme": "주제"},
        ]
        result = design_season_arc(episodes)

        assert result.episodes[0].title == "에피소드 1"
        assert result.episodes[1].title == "제목 있음"

    def test_missing_theme_uses_empty(self):
        """theme이 없는 에피소드는 빈 문자열을 사용한다."""
        episodes = [{"title": "제목만 있음"}]
        result = design_season_arc(episodes)

        assert result.episodes[0].theme == ""

    def test_large_episode_count(self):
        """많은 에피소드에서도 정상 동작한다."""
        episodes = [
            {"title": f"EP{i}", "theme": f"T{i}"}
            for i in range(20)
        ]
        result = design_season_arc(episodes)

        assert result.total_episodes == 20
        assert len(result.episodes) == 20
        # 모든 에피소드에 역할이 배정됨
        for ep in result.episodes:
            assert ep.role_in_arc != ""

    def test_season_title_from_themes(self):
        """에피소드 테마에서 시즌 제목을 생성한다."""
        episodes = [
            {"title": "EP1", "theme": "요리 입문"},
            {"title": "EP2", "theme": "요리 심화"},
            {"title": "EP3", "theme": "요리 마스터"},
        ]
        result = design_season_arc(episodes)
        # "요리"가 가장 빈번하므로 제목에 포함
        assert "요리" in result.season_title


class TestAssignRoles:
    """_assign_roles 함수 테스트"""

    def test_zero_count(self):
        """0개 에피소드에는 빈 역할 리스트를 반환한다."""
        assert _assign_roles(0, "rising") == []

    def test_roles_match_count(self):
        """에피소드 수만큼 역할이 배분된다."""
        roles = _assign_roles(5, "rising")
        assert len(roles) == 5

    def test_large_count_roles(self):
        """템플릿보다 많은 에피소드도 처리한다."""
        roles = _assign_roles(10, "mystery")
        assert len(roles) == 10


class TestDetectArcType:
    """_detect_arc_type 함수 테스트"""

    def test_empty_episodes(self):
        """빈 에피소드는 rising을 반환한다."""
        assert _detect_arc_type([]) == "rising"

    def test_keyword_priority(self):
        """미스터리 키워드가 우선 감지된다."""
        episodes = [{"title": "비밀과 성장", "theme": "mystery와 growth"}]
        assert _detect_arc_type(episodes) == "mystery"
