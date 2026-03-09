"""
장면 스키마 서비스 — 비디오 장면을 구조화된 스키마로 표현
"""

import re
import uuid
from dataclasses import dataclass, field


# 장면 유형별 키워드 매핑
_SCENE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "intro": [
        "시작", "인사", "안녕", "소개", "오늘", "환영", "hello", "hi",
        "welcome", "intro", "introduction", "start", "begin",
    ],
    "exposition": [
        "설명", "배경", "개념", "정의", "기본", "이론", "원리",
        "explain", "concept", "definition", "background", "theory",
        "what is", "means", "basically",
    ],
    "climax": [
        "핵심", "중요", "결정적", "놀라운", "반전", "주목", "비밀",
        "key", "important", "crucial", "critical", "amazing", "secret",
        "breakthrough", "revelation", "insight",
    ],
    "conclusion": [
        "결론", "정리", "마무리", "요약", "끝", "마지막", "감사",
        "conclusion", "summary", "wrap", "final", "end", "thank",
        "recap", "closing",
    ],
    "transition": [
        "다음", "그런데", "한편", "또한", "그리고", "반면",
        "next", "however", "meanwhile", "also", "furthermore",
        "on the other hand", "moving on", "let's move",
    ],
}


@dataclass
class SceneSchema:
    """장면 스키마"""
    scene_id: str
    scene_type: str  # intro / exposition / climax / conclusion / transition
    participants: list[str] = field(default_factory=list)
    setting: str = ""
    emotion: str = ""
    key_dialogue: list[str] = field(default_factory=list)
    duration_sec: float = 0.0


def classify_scene_type(description: str) -> str:
    """장면 유형 분류 (키워드 기반)

    Args:
        description: 장면 설명 텍스트

    Returns:
        장면 유형 (intro/exposition/climax/conclusion/transition)
    """
    if not description.strip():
        return "exposition"  # 기본값

    desc_lower = description.lower()
    scores: dict[str, int] = {}

    for scene_type, keywords in _SCENE_TYPE_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if keyword in desc_lower:
                score += 1
        scores[scene_type] = score

    # 최고 점수 유형 반환 (동점이면 기본 exposition)
    max_score = max(scores.values())
    if max_score == 0:
        return "exposition"

    for scene_type in ["intro", "climax", "conclusion", "transition", "exposition"]:
        if scores.get(scene_type, 0) == max_score:
            return scene_type

    return "exposition"


def extract_schema(transcript_segment: str, timestamp: float = 0.0) -> SceneSchema:
    """자막 세그먼트에서 스키마 추출

    Args:
        transcript_segment: 자막 텍스트
        timestamp: 타임스탬프 (초)

    Returns:
        추출된 장면 스키마
    """
    if not transcript_segment.strip():
        return SceneSchema(
            scene_id=str(uuid.uuid4()),
            scene_type="exposition",
            duration_sec=timestamp,
        )

    # 장면 유형 분류
    scene_type = classify_scene_type(transcript_segment)

    # 대화 추출 (따옴표 내 텍스트)
    dialogues = re.findall(r'["\u201c\u201d"\'](.*?)["\u201c\u201d"\']', transcript_segment)
    if not dialogues:
        # 문장 단위로 핵심 대사 추출 (짧은 문장)
        sentences = re.split(r"[.!?。\n]+", transcript_segment)
        dialogues = [s.strip() for s in sentences if 3 < len(s.strip()) < 100][:3]

    # 감정 추출 (키워드 기반)
    emotion = _detect_emotion(transcript_segment)

    return SceneSchema(
        scene_id=str(uuid.uuid4()),
        scene_type=scene_type,
        participants=[],
        setting="",
        emotion=emotion,
        key_dialogue=dialogues[:5],
        duration_sec=timestamp,
    )


def _detect_emotion(text: str) -> str:
    """텍스트에서 감정 감지 (키워드 기반)"""
    text_lower = text.lower()

    emotion_keywords: dict[str, list[str]] = {
        "excited": ["신나", "흥미", "exciting", "amazing", "awesome", "wow"],
        "serious": ["심각", "중요", "serious", "critical", "important"],
        "humorous": ["웃기", "재미", "funny", "hilarious", "joke", "lol"],
        "calm": ["차분", "평온", "calm", "peaceful", "relaxed"],
        "tense": ["긴장", "불안", "tense", "nervous", "worried", "anxiety"],
    }

    for emotion, keywords in emotion_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                return emotion

    return "neutral"


def build_sequence(schemas: list[SceneSchema]) -> list[dict]:
    """장면 시퀀스 빌드 (전환 분석)

    Args:
        schemas: 장면 스키마 목록

    Returns:
        전환 정보가 포함된 시퀀스 목록
    """
    if not schemas:
        return []

    sequence: list[dict] = []

    for i, schema in enumerate(schemas):
        entry: dict = {
            "index": i,
            "scene_id": schema.scene_id,
            "scene_type": schema.scene_type,
            "emotion": schema.emotion,
            "duration_sec": schema.duration_sec,
            "dialogue_count": len(schema.key_dialogue),
        }

        # 전환 분석 (이전 장면과 비교)
        if i > 0:
            prev = schemas[i - 1]
            entry["transition_from"] = prev.scene_type
            entry["type_changed"] = prev.scene_type != schema.scene_type
            entry["emotion_changed"] = prev.emotion != schema.emotion
        else:
            entry["transition_from"] = None
            entry["type_changed"] = False
            entry["emotion_changed"] = False

        sequence.append(entry)

    return sequence


def analyze_pacing(schemas: list[SceneSchema]) -> dict:
    """페이싱 분석 (장면 유형별 비율, 평균 길이)

    Args:
        schemas: 장면 스키마 목록

    Returns:
        분석 결과 딕셔너리
    """
    if not schemas:
        return {
            "total_scenes": 0,
            "type_distribution": {},
            "avg_duration": 0.0,
            "type_avg_duration": {},
        }

    total = len(schemas)

    # 유형별 카운트 및 시간
    type_counts: dict[str, int] = {}
    type_durations: dict[str, list[float]] = {}

    for schema in schemas:
        t = schema.scene_type
        type_counts[t] = type_counts.get(t, 0) + 1
        if t not in type_durations:
            type_durations[t] = []
        type_durations[t].append(schema.duration_sec)

    # 유형별 비율
    type_distribution = {
        t: round(count / total, 3) for t, count in type_counts.items()
    }

    # 전체 평균 길이
    all_durations = [s.duration_sec for s in schemas]
    avg_duration = round(sum(all_durations) / total, 2) if total > 0 else 0.0

    # 유형별 평균 길이
    type_avg_duration = {
        t: round(sum(durations) / len(durations), 2)
        for t, durations in type_durations.items()
    }

    return {
        "total_scenes": total,
        "type_distribution": type_distribution,
        "avg_duration": avg_duration,
        "type_avg_duration": type_avg_duration,
    }
