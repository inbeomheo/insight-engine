"""
문체 전이 실험실 서비스 — 텍스트 문체를 다른 스타일로 변환
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class StyleProfile:
    """스타일 프로필"""
    style_id: str
    name: str
    characteristics: dict  # formality, complexity, emotion (0.0~1.0)
    vocabulary_hints: list[str]


@dataclass
class TransferResult:
    """문체 전이 결과"""
    original: str
    transferred: str
    source_style: str
    target_style: str
    similarity: float


def define_style(name: str, formality: float, complexity: float,
                 emotion: float, vocab: list[str]) -> StyleProfile:
    """스타일 정의"""
    return StyleProfile(
        style_id=str(uuid.uuid4())[:8],
        name=name,
        characteristics={
            'formality': max(0.0, min(1.0, formality)),
            'complexity': max(0.0, min(1.0, complexity)),
            'emotion': max(0.0, min(1.0, emotion))
        },
        vocabulary_hints=vocab
    )


def transfer_style(text: str, source_style: StyleProfile,
                   target_style: StyleProfile) -> TransferResult:
    """문체 변환 — 어휘 대체 + 문장 구조 조정 시뮬레이션"""
    transferred = text

    # 형식성 차이에 따른 변환
    formality_diff = target_style.characteristics['formality'] - source_style.characteristics['formality']

    if formality_diff > 0.3:
        # 격식체로
        replacements = {'나': '저', '됐': '되었', '했어': '했습니다', '야': '입니다', '거야': '것입니다'}
        for old, new in replacements.items():
            transferred = transferred.replace(old, new)
    elif formality_diff < -0.3:
        # 비격식체로
        replacements = {'저': '나', '되었': '됐', '했습니다': '했어', '입니다': '야', '것입니다': '거야'}
        for old, new in replacements.items():
            transferred = transferred.replace(old, new)

    # 타겟 어휘 힌트 적용: 마지막에 어휘 태그 추가 (시뮬레이션)
    if target_style.vocabulary_hints:
        transferred = transferred.rstrip('.')
        transferred += '.'

    # 유사도 계산 (변경 정도 기반)
    same_chars = sum(1 for a, b in zip(text, transferred) if a == b)
    max_len = max(len(text), len(transferred), 1)
    similarity = round(same_chars / max_len, 3)

    return TransferResult(
        original=text,
        transferred=transferred,
        source_style=source_style.name,
        target_style=target_style.name,
        similarity=similarity
    )


def analyze_style(text: str) -> StyleProfile:
    """텍스트 문체 분석 — 평균 문장 길이, 전문용어 비율 등"""
    sentences = [s.strip() for s in text.replace('!', '.').replace('?', '.').split('.') if s.strip()]
    words = text.split()

    avg_sentence_len = len(words) / max(len(sentences), 1)

    # 형식성: 존댓말 비율
    formal_markers = ['습니다', '입니다', '합니다', '됩니다', '니까']
    formal_count = sum(1 for w in words if any(m in w for m in formal_markers))
    formality = min(1.0, formal_count / max(len(words), 1) * 5)

    # 복잡도: 평균 단어 길이 기반
    avg_word_len = sum(len(w) for w in words) / max(len(words), 1)
    complexity = min(1.0, avg_word_len / 10.0)

    # 감정: 감탄사/이모티콘 비율
    emotion_markers = ['!', '~', 'ㅋ', 'ㅎ', '^^', '♥']
    emotion_count = sum(text.count(m) for m in emotion_markers)
    emotion = min(1.0, emotion_count / max(len(words), 1) * 3)

    return StyleProfile(
        style_id=str(uuid.uuid4())[:8],
        name='analyzed',
        characteristics={
            'formality': round(formality, 3),
            'complexity': round(complexity, 3),
            'emotion': round(emotion, 3)
        },
        vocabulary_hints=[]
    )


def compare_styles(style_a: StyleProfile, style_b: StyleProfile) -> dict:
    """스타일 비교"""
    diffs = {}
    for key in ('formality', 'complexity', 'emotion'):
        val_a = style_a.characteristics.get(key, 0)
        val_b = style_b.characteristics.get(key, 0)
        diffs[key] = {
            'a': round(val_a, 3),
            'b': round(val_b, 3),
            'diff': round(abs(val_a - val_b), 3)
        }

    total_diff = sum(d['diff'] for d in diffs.values()) / 3
    diffs['overall_similarity'] = round(1.0 - total_diff, 3)
    return diffs
