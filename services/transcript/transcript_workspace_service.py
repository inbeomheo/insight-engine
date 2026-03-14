"""
자막 워크스페이스 서비스

자막 텍스트를 문장 단위로 분리하고, 사용자 편집(삭제/수정)을 적용하는 기능 제공.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# 문장 종결 패턴 (한국어 + 영어)
_SENTENCE_END = re.compile(
    r'(?<=[.!?。？！])\s+'      # 마침표/느낌표/물음표 뒤 공백
    r'|(?<=다\.)\s+'            # 한국어 "~다." 패턴
    r'|(?<=요\.)\s+'            # 한국어 "~요." 패턴
    r'|(?<=니다\.)\s+'          # 한국어 "~니다." 패턴
)


def parse_transcript_sentences(
    transcript_text: str,
    segments: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """자막 텍스트를 문장 단위로 분리하고 타임스탬프를 매핑합니다.

    Args:
        transcript_text: 전체 자막 텍스트 (공백으로 연결된 형태)
        segments: 타임스탬프 포함 세그먼트 목록
                  [{'start': float, 'text': str, 'duration': float}, ...]

    Returns:
        문장 목록 [{'index': int, 'text': str, 'start_time': float | None}, ...]
    """
    if not transcript_text or not transcript_text.strip():
        return []

    # 세그먼트가 있으면 세그먼트 기반 문장 분리
    if segments:
        return _parse_with_segments(segments)

    # 세그먼트 없으면 텍스트 기반 문장 분리
    return _parse_text_only(transcript_text)


def _parse_with_segments(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """세그먼트(타임스탬프 포함)를 활용하여 문장을 분리합니다."""
    sentences: List[Dict[str, Any]] = []
    buffer = ''
    buffer_start: Optional[float] = None

    for seg in segments:
        text = (seg.get('text') or '').strip()
        start = seg.get('start')

        if not text:
            continue

        if buffer_start is None:
            buffer_start = start

        buffer += (' ' if buffer else '') + text

        # 문장 종결 패턴 확인
        parts = _SENTENCE_END.split(buffer)
        if len(parts) > 1:
            # 마지막 조각은 다음 문장의 시작이므로 버퍼에 유지
            for part in parts[:-1]:
                part = part.strip()
                if part:
                    sentences.append({
                        'index': len(sentences),
                        'text': part,
                        'start_time': buffer_start,
                    })
            buffer = parts[-1].strip()
            # 다음 문장의 시작 시각은 현재 세그먼트의 start
            buffer_start = start if buffer else None

    # 남은 버퍼 처리
    if buffer.strip():
        sentences.append({
            'index': len(sentences),
            'text': buffer.strip(),
            'start_time': buffer_start,
        })

    return sentences


def _parse_text_only(transcript_text: str) -> List[Dict[str, Any]]:
    """타임스탬프 없이 텍스트만으로 문장을 분리합니다."""
    parts = _SENTENCE_END.split(transcript_text.strip())
    sentences: List[Dict[str, Any]] = []

    for part in parts:
        part = part.strip()
        if part:
            sentences.append({
                'index': len(sentences),
                'text': part,
                'start_time': None,
            })

    # 분리가 안 되면 원본 그대로 1문장
    if not sentences and transcript_text.strip():
        sentences.append({
            'index': 0,
            'text': transcript_text.strip(),
            'start_time': None,
        })

    return sentences


def apply_edits(
    sentences: List[Dict[str, Any]],
    edits: Dict[str, Any],
) -> str:
    """사용자 편집을 적용하여 수정된 자막 텍스트를 반환합니다.

    Args:
        sentences: parse_transcript_sentences()가 반환한 문장 목록
        edits: 편집 내용
            - deleted: list[int] — 삭제할 문장 index 목록
            - modified: dict[str, str] — {index(str): 수정된 텍스트} 매핑

    Returns:
        편집이 적용된 전체 자막 텍스트
    """
    deleted_indices = set(edits.get('deleted', []))
    modified_map: Dict[str, str] = edits.get('modified', {})

    result_parts: List[str] = []

    for sentence in sentences:
        idx = sentence.get('index', -1)

        # 삭제된 문장은 건너뜀
        if idx in deleted_indices:
            continue

        # 수정된 문장은 수정본 사용
        idx_str = str(idx)
        if idx_str in modified_map:
            text = modified_map[idx_str].strip()
        else:
            text = sentence.get('text', '').strip()

        if text:
            result_parts.append(text)

    return ' '.join(result_parts)
