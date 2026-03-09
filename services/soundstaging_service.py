"""
사운드스테이징 디자인 서비스

스크립트와 환경 설정에 따라 사운드 레이어(음원 배치)를 설계합니다.
외부 API 없이 규칙 기반으로 동작합니다.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

SUPPORTED_ENVIRONMENTS = ('studio', 'outdoor', 'stage', 'virtual')


@dataclass
class SoundLayer:
    """사운드 레이어"""
    name: str
    type: str      # "voice", "bgm", "sfx", "ambience"
    position: str  # "center", "left", "right", "surround", "overhead"
    volume: float  # 0.0 ~ 1.0


@dataclass
class SoundstageDesign:
    """사운드스테이징 디자인"""
    environment: str
    layers: List[SoundLayer] = field(default_factory=list)
    spatial_notes: List[str] = field(default_factory=list)


# 환경별 기본 레이어 설정
_ENVIRONMENT_PRESETS = {
    'studio': {
        'base_layers': [
            SoundLayer(name='Main Voice', type='voice', position='center', volume=0.9),
            SoundLayer(name='Room Tone', type='ambience', position='surround', volume=0.1),
        ],
        'notes': [
            '스튜디오 환경: 데드 사운드(잔향 최소화) 권장',
            '보이스를 센터에 배치하여 명료도를 극대화하세요',
        ],
    },
    'outdoor': {
        'base_layers': [
            SoundLayer(name='Main Voice', type='voice', position='center', volume=0.85),
            SoundLayer(name='Wind Ambience', type='ambience', position='surround', volume=0.2),
            SoundLayer(name='Nature Sounds', type='sfx', position='left', volume=0.15),
        ],
        'notes': [
            '야외 환경: 바람 소리를 서라운드로 배치하여 공간감을 연출하세요',
            '보이스 볼륨을 약간 높여 배경 소음을 보상하세요',
        ],
    },
    'stage': {
        'base_layers': [
            SoundLayer(name='Main Voice', type='voice', position='center', volume=0.85),
            SoundLayer(name='Stage BGM', type='bgm', position='surround', volume=0.3),
            SoundLayer(name='Audience Ambience', type='ambience', position='surround', volume=0.15),
            SoundLayer(name='Stage Effects', type='sfx', position='overhead', volume=0.2),
        ],
        'notes': [
            '무대 환경: 관객 분위기를 서라운드에 배치하세요',
            '효과음은 오버헤드로 공간 깊이를 더하세요',
        ],
    },
    'virtual': {
        'base_layers': [
            SoundLayer(name='Main Voice', type='voice', position='center', volume=0.9),
            SoundLayer(name='Digital Ambience', type='ambience', position='surround', volume=0.15),
            SoundLayer(name='UI Sound Effects', type='sfx', position='right', volume=0.1),
        ],
        'notes': [
            '가상 환경: 디지털 앰비언스로 몰입감을 높이세요',
            'UI 효과음을 우측에 배치하여 공간 분리를 도우세요',
        ],
    },
}

# 키워드 기반 추가 레이어 규칙
_KEYWORD_LAYERS = [
    {
        'keywords': ['음악', 'bgm', '배경음악', 'music', 'song'],
        'layer': SoundLayer(name='Background Music', type='bgm', position='surround', volume=0.25),
    },
    {
        'keywords': ['효과음', 'sfx', 'sound effect', '사운드'],
        'layer': SoundLayer(name='Sound Effects', type='sfx', position='left', volume=0.2),
    },
    {
        'keywords': ['나레이션', 'narration', '내레이션', '해설'],
        'layer': SoundLayer(name='Narration', type='voice', position='center', volume=0.85),
    },
    {
        'keywords': ['인터뷰', 'interview', '대화', 'dialogue'],
        'layer': SoundLayer(name='Guest Voice', type='voice', position='right', volume=0.8),
    },
]


def _detect_additional_layers(script: str) -> List[SoundLayer]:
    """스크립트 키워드에서 추가 레이어를 감지합니다."""
    additional = []
    script_lower = script.lower()
    added_names = set()

    for rule in _KEYWORD_LAYERS:
        for keyword in rule['keywords']:
            if keyword in script_lower and rule['layer'].name not in added_names:
                additional.append(rule['layer'])
                added_names.add(rule['layer'].name)
                break

    return additional


def design_soundstage(
    script: str,
    environment: str = 'studio',
) -> SoundstageDesign:
    """
    스크립트와 환경에 맞는 사운드스테이징을 설계합니다.

    Args:
        script: 스크립트 텍스트
        environment: 환경 타입 ("studio", "outdoor", "stage", "virtual")

    Returns:
        SoundstageDesign 결과

    Raises:
        ValueError: 지원하지 않는 환경 타입인 경우
    """
    if environment not in SUPPORTED_ENVIRONMENTS:
        raise ValueError(
            f'지원하지 않는 환경: {environment}. '
            f'지원 목록: {list(SUPPORTED_ENVIRONMENTS)}'
        )

    if not script or not script.strip():
        preset = _ENVIRONMENT_PRESETS[environment]
        return SoundstageDesign(
            environment=environment,
            layers=list(preset['base_layers']),
            spatial_notes=['입력 스크립트가 비어 있어 기본 레이어만 적용했습니다'],
        )

    preset = _ENVIRONMENT_PRESETS[environment]
    layers = list(preset['base_layers'])
    notes = list(preset['notes'])

    # 스크립트 키워드 기반 추가 레이어
    additional = _detect_additional_layers(script)
    existing_names = {layer.name for layer in layers}
    for layer in additional:
        if layer.name not in existing_names:
            layers.append(layer)
            existing_names.add(layer.name)
            notes.append(f'"{layer.name}" 레이어를 스크립트 키워드 기반으로 추가했습니다')

    # 볼륨 총합 검증 (1.5 초과 시 경고)
    total_volume = sum(l.volume for l in layers)
    if total_volume > 1.5:
        notes.append(f'총 볼륨({total_volume:.2f})이 높습니다. 레이어 간 볼륨 밸런스를 조정하세요')

    return SoundstageDesign(
        environment=environment,
        layers=layers,
        spatial_notes=notes,
    )
