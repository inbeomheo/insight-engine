"""시즌 구성 설계 서비스 — 에피소드 목록으로 시즌 아크 설계"""
import re
from dataclasses import dataclass, field


@dataclass
class EpisodePlan:
    """에피소드 계획"""
    episode_number: int
    title: str
    theme: str
    role_in_arc: str  # intro, build, climax, resolution 등


@dataclass
class SeasonArc:
    """시즌 아크 구조"""
    season_title: str
    episodes: list  # list[EpisodePlan]
    arc_type: str  # rising, episodic, mystery, transformation
    total_episodes: int


# 아크 유형별 역할 배분 비율
_ARC_ROLE_TEMPLATES = {
    "rising": ["intro", "build", "build", "climax", "resolution"],
    "episodic": ["standalone", "standalone", "standalone", "standalone", "standalone"],
    "mystery": ["setup", "clue", "clue", "reveal", "resolution"],
    "transformation": ["before", "catalyst", "struggle", "breakthrough", "after"],
}

_VALID_ARC_TYPES = set(_ARC_ROLE_TEMPLATES.keys())


def _detect_arc_type(episodes: list[dict]) -> str:
    """에피소드 제목/테마에서 아크 유형을 추론한다."""
    all_text = " ".join(
        (ep.get("title", "") + " " + ep.get("theme", "")).lower()
        for ep in episodes
    )

    # 키워드 매칭으로 아크 유형 추정
    if any(kw in all_text for kw in ["미스터리", "mystery", "단서", "clue", "비밀", "secret"]):
        return "mystery"
    if any(kw in all_text for kw in ["변화", "transform", "성장", "growth", "변신"]):
        return "transformation"
    if any(kw in all_text for kw in ["독립", "standalone", "옴니버스", "omnibus"]):
        return "episodic"
    return "rising"


def _assign_roles(count: int, arc_type: str) -> list[str]:
    """에피소드 수에 맞게 아크 역할을 배분한다."""
    template = _ARC_ROLE_TEMPLATES[arc_type]
    if count <= 0:
        return []
    if count <= len(template):
        # 템플릿에서 균등 샘플링
        step = len(template) / count
        return [template[int(i * step)] for i in range(count)]
    # 에피소드가 템플릿보다 많으면 중간 역할 반복
    roles = [template[0]]
    middle = template[1:-1] if len(template) > 2 else [template[0]]
    for i in range(1, count - 1):
        roles.append(middle[i % len(middle)])
    roles.append(template[-1])
    return roles


def _generate_season_title(episodes: list[dict]) -> str:
    """에피소드 테마에서 시즌 제목을 생성한다."""
    themes = [ep.get("theme", "") for ep in episodes if ep.get("theme")]
    if not themes:
        titles = [ep.get("title", "") for ep in episodes if ep.get("title")]
        if titles:
            return f"{titles[0]} 시즌"
        return "새로운 시즌"

    # 가장 빈번한 키워드를 제목에 반영
    words = []
    for t in themes:
        words.extend(re.findall(r'[가-힣a-zA-Z]+', t))
    if not words:
        return f"{themes[0]} 시즌"

    # 빈도 상위 단어 추출
    freq: dict[str, int] = {}
    for w in words:
        if len(w) > 1:
            freq[w] = freq.get(w, 0) + 1
    if freq:
        top_word = max(freq, key=lambda k: freq[k])
        return f"{top_word} 시즌"
    return f"{themes[0]} 시즌"


def design_season_arc(episodes: list[dict]) -> SeasonArc:
    """에피소드 목록으로 시즌 아크를 설계한다.

    Args:
        episodes: [{"title": str, "theme": str}, ...] 형태의 에피소드 목록

    Returns:
        SeasonArc 구조
    """
    if not episodes:
        return SeasonArc(
            season_title="빈 시즌",
            episodes=[],
            arc_type="episodic",
            total_episodes=0,
        )

    arc_type = _detect_arc_type(episodes)
    roles = _assign_roles(len(episodes), arc_type)
    season_title = _generate_season_title(episodes)

    episode_plans = []
    for i, ep in enumerate(episodes):
        plan = EpisodePlan(
            episode_number=i + 1,
            title=ep.get("title", f"에피소드 {i + 1}"),
            theme=ep.get("theme", ""),
            role_in_arc=roles[i] if i < len(roles) else "build",
        )
        episode_plans.append(plan)

    return SeasonArc(
        season_title=season_title,
        episodes=episode_plans,
        arc_type=arc_type,
        total_episodes=len(episode_plans),
    )
