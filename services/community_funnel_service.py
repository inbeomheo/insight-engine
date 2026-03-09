"""
커뮤니티 퍼널 서비스

무료→유료 전환 퍼널을 설계합니다.
tier 정보를 입력받아 4단계 퍼널 구조를 자동 생성.
순수 규칙 기반, 외부 API 호출 없음.
"""
from dataclasses import dataclass, field


@dataclass
class FunnelStage:
    """퍼널 단계"""
    name: str  # 단계 이름
    tier_level: int  # 대응 tier (0 = 무료, 1+ = 유료)
    content_type: str  # 제공 콘텐츠 유형
    access: str  # 접근 권한 ("free", "limited", "paid", "vip")
    conversion_action: str  # 다음 단계로 전환시키기 위한 행동


@dataclass
class FunnelDesign:
    """퍼널 설계 결과"""
    stages: list[FunnelStage]
    conversion_targets: dict  # 단계별 목표 전환율
    total_tiers: int  # 총 tier 수


# 기본 4단계 퍼널 템플릿
_DEFAULT_STAGES = [
    {
        "name": "awareness",
        "content_type": "무료 콘텐츠 (블로그, SNS, YouTube)",
        "access": "free",
        "conversion_action": "이메일 구독 유도",
    },
    {
        "name": "interest",
        "content_type": "뉴스레터, 무료 가이드, 샘플 강의",
        "access": "limited",
        "conversion_action": "무료 체험 등록",
    },
    {
        "name": "consideration",
        "content_type": "체험판 콘텐츠, 커뮤니티 미리보기",
        "access": "limited",
        "conversion_action": "유료 구독 전환",
    },
    {
        "name": "conversion",
        "content_type": "프리미엄 콘텐츠, 1:1 코칭, 독점 자료",
        "access": "paid",
        "conversion_action": "상위 tier 업그레이드",
    },
]

# 기본 전환 목표
_DEFAULT_CONVERSION_TARGETS = {
    "awareness_to_interest": 0.15,
    "interest_to_consideration": 0.10,
    "consideration_to_conversion": 0.05,
}

# tier 레벨별 콘텐츠 유형/접근 권한 매핑
_TIER_CONTENT_MAP = {
    0: {"content_type": "공개 콘텐츠 (블로그, SNS, 유튜브)", "access": "free"},
    1: {"content_type": "기본 유료 콘텐츠 (뉴스레터, 아카이브)", "access": "limited"},
    2: {"content_type": "심화 콘텐츠 (강의, 워크시트, 커뮤니티)", "access": "paid"},
    3: {"content_type": "프리미엄 독점 (1:1 코칭, 얼리액세스, VIP)", "access": "vip"},
}

_TIER_CONVERSION_ACTIONS = {
    0: "이메일/SNS 구독 유도",
    1: "유료 구독 체험 제공",
    2: "상위 tier 혜택 안내",
    3: "장기 구독/연간 플랜 제안",
}


def _map_tier_to_stage(tier: dict, index: int, total: int) -> FunnelStage:
    """개별 tier를 퍼널 단계로 매핑합니다."""
    tier_level = tier.get('level', index)
    tier_name = tier.get('name', f"tier_{tier_level}")

    # 4단계 중 어디에 해당하는지 매핑
    stage_names = ["awareness", "interest", "consideration", "conversion"]
    if total <= 1:
        stage_name = "conversion"
    elif index == 0:
        stage_name = "awareness"
    elif index == total - 1:
        stage_name = "conversion"
    elif index <= total // 2:
        stage_name = "interest"
    else:
        stage_name = "consideration"

    # tier 레벨에 따른 콘텐츠/접근 매핑
    clamped_level = min(tier_level, 3)
    mapping = _TIER_CONTENT_MAP.get(clamped_level, _TIER_CONTENT_MAP[3])
    action = _TIER_CONVERSION_ACTIONS.get(clamped_level, _TIER_CONVERSION_ACTIONS[3])

    # tier에 커스텀 정보가 있으면 우선 사용
    content_type = tier.get('content_type', mapping['content_type'])
    access = tier.get('access', mapping['access'])
    conversion_action = tier.get('conversion_action', action)

    return FunnelStage(
        name=f"{stage_name}_{tier_name}",
        tier_level=tier_level,
        content_type=content_type,
        access=access,
        conversion_action=conversion_action,
    )


def design_funnel(tiers: list[dict]) -> FunnelDesign:
    """무료→유료 전환 퍼널을 설계합니다.

    Args:
        tiers: tier 정보 리스트. 각 dict에 level(int), name(str) 등 포함.
              예: [{"level": 0, "name": "free"}, {"level": 1, "name": "basic"}, ...]

    Returns:
        FunnelDesign — 퍼널 단계, 전환 목표, tier 수
    """
    if not tiers:
        # tier가 없으면 기본 4단계 퍼널 반환
        stages = [
            FunnelStage(
                name=s["name"],
                tier_level=idx,
                content_type=s["content_type"],
                access=s["access"],
                conversion_action=s["conversion_action"],
            )
            for idx, s in enumerate(_DEFAULT_STAGES)
        ]
        return FunnelDesign(
            stages=stages,
            conversion_targets=dict(_DEFAULT_CONVERSION_TARGETS),
            total_tiers=4,
        )

    # tier를 level 순으로 정렬
    sorted_tiers = sorted(tiers, key=lambda t: t.get('level', 0))
    total = len(sorted_tiers)

    stages = [
        _map_tier_to_stage(tier, idx, total)
        for idx, tier in enumerate(sorted_tiers)
    ]

    # 전환 목표 자동 생성 (단계가 많을수록 각 단계 전환율 낮게)
    conversion_targets = {}
    for i in range(len(stages) - 1):
        key = f"{stages[i].name}_to_{stages[i + 1].name}"
        # 기본 15% → 단계 수에 따라 감소
        base_rate = 0.15
        decay = 0.7 ** i  # 뒤로 갈수록 전환율 감소
        conversion_targets[key] = round(base_rate * decay, 3)

    return FunnelDesign(
        stages=stages,
        conversion_targets=conversion_targets,
        total_tiers=total,
    )
