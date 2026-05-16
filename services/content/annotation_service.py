"""
콘텐츠 주석(Annotation) 서비스

콘텐츠에 인라인 주석을 삽입하거나 추출합니다.
주석 형식: <!-- @note: 주석 내용 --> 또는 <!-- @todo: 할일 -->
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# 주석 패턴: <!-- @type: content -->
_ANNOTATION_PATTERN = re.compile(
    r'<!--\s*@(\w+)\s*:\s*(.+?)\s*-->', re.DOTALL
)

ANNOTATION_TYPES = {
    'note': {'label': '참고', 'color': '#3b82f6'},
    'todo': {'label': '할일', 'color': '#f59e0b'},
    'warn': {'label': '주의', 'color': '#ef4444'},
    'review': {'label': '검토', 'color': '#8b5cf6'},
    'source': {'label': '출처', 'color': '#10b981'},
}


def add_annotation(content: str, position: int, annotation_type: str,
                   text: str) -> dict:
    """콘텐츠의 특정 위치에 주석을 삽입합니다.

    Args:
        content: 원본 콘텐츠
        position: 삽입 위치 (문자 인덱스, -1이면 끝에 추가)
        annotation_type: 주석 유형 (note/todo/warn/review/source)
        text: 주석 내용

    Returns:
        {'annotated': str, 'annotation_id': str, 'position': int}
    """
    if not content:
        return {'annotated': '', 'annotation_id': '', 'position': 0}

    if annotation_type not in ANNOTATION_TYPES:
        annotation_type = 'note'

    annotation = f'<!-- @{annotation_type}: {text} -->'

    if position < 0 or position >= len(content):
        annotated = content + '\n' + annotation
        actual_pos = len(content)
    else:
        annotated = content[:position] + annotation + content[position:]
        actual_pos = position

    # 간단한 ID 생성
    annotation_id = f'{annotation_type}_{actual_pos}'

    return {
        'annotated': annotated,
        'annotation_id': annotation_id,
        'position': actual_pos,
    }


def extract_annotations(content: str) -> dict:
    """콘텐츠에서 모든 주석을 추출합니다.

    Returns:
        {
            'annotations': [{'type': str, 'text': str, 'position': int, 'label': str}],
            'total': int,
            'by_type': {type: count},
        }
    """
    if not content:
        return {'annotations': [], 'total': 0, 'by_type': {}}

    annotations: List[dict] = []
    by_type: dict = {}

    for match in _ANNOTATION_PATTERN.finditer(content):
        ann_type = match.group(1).lower()
        ann_text = match.group(2).strip()
        position = match.start()

        type_info = ANNOTATION_TYPES.get(ann_type, {'label': ann_type, 'color': '#6b7280'})
        annotations.append({
            'type': ann_type,
            'text': ann_text,
            'position': position,
            'label': type_info['label'],
        })
        by_type[ann_type] = by_type.get(ann_type, 0) + 1

    return {
        'annotations': annotations,
        'total': len(annotations),
        'by_type': by_type,
    }


def remove_annotations(content: str, annotation_type: str = '') -> dict:
    """콘텐츠에서 주석을 제거합니다.

    Args:
        content: 원본 콘텐츠
        annotation_type: 제거할 유형 (빈 문자열이면 모든 주석 제거)

    Returns:
        {'cleaned': str, 'removed_count': int}
    """
    if not content:
        return {'cleaned': '', 'removed_count': 0}

    count = 0
    if annotation_type:
        pattern = re.compile(rf'<!--\s*@{re.escape(annotation_type)}\s*:\s*.+?\s*-->\n?', re.DOTALL)
    else:
        pattern = re.compile(r'<!--\s*@\w+\s*:\s*.+?\s*-->\n?', re.DOTALL)

    def count_and_remove(match):
        nonlocal count
        count += 1
        return ''

    cleaned = pattern.sub(count_and_remove, content)
    # 연속 빈 줄 정리
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return {
        'cleaned': cleaned.strip(),
        'removed_count': count,
    }


def get_annotation_types() -> list:
    """지원하는 주석 유형 목록."""
    return [
        {'id': tid, 'label': info['label'], 'color': info['color']}
        for tid, info in ANNOTATION_TYPES.items()
    ]
