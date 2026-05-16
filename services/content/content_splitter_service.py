"""
콘텐츠 분할(Splitter) 서비스

긴 콘텐츠를 시리즈/파트로 분할합니다.
헤딩 기준 또는 글자수 기준으로 분할 가능.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
_WORD_PATTERN = re.compile(r'[\w가-힣]+')


def split_by_headings(content: str, split_level: int = 2) -> dict:
    """헤딩 기준으로 콘텐츠를 분할합니다.

    Args:
        content: 원본 콘텐츠
        split_level: 분할 기준 헤딩 레벨 (1=H1, 2=H2, 3=H3)

    Returns:
        {
            'parts': [{'title': str, 'content': str, 'word_count': int, 'part_number': int}],
            'total_parts': int,
            'total_words': int,
        }
    """
    if not content or not content.strip():
        return {'parts': [], 'total_parts': 0, 'total_words': 0}

    split_level = max(1, min(3, split_level))
    text = content.strip()
    lines = text.split('\n')

    parts: List[dict] = []
    current_title = ''
    current_lines: List[str] = []

    for line in lines:
        match = _HEADING_PATTERN.match(line)
        if match and len(match.group(1)) <= split_level:
            # 이전 파트 저장
            if current_lines or current_title:
                body = '\n'.join(current_lines).strip()
                if body or current_title:
                    parts.append(_make_part(current_title, body, len(parts) + 1))
            current_title = match.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # 마지막 파트
    body = '\n'.join(current_lines).strip()
    if body or current_title:
        parts.append(_make_part(current_title, body, len(parts) + 1))

    total_words = sum(p['word_count'] for p in parts)

    return {
        'parts': parts,
        'total_parts': len(parts),
        'total_words': total_words,
    }


def split_by_length(content: str, max_chars: int = 2000) -> dict:
    """글자수 기준으로 콘텐츠를 분할합니다.

    문단 경계에서 분할하여 문장이 잘리지 않도록 합니다.

    Args:
        content: 원본 콘텐츠
        max_chars: 파트당 최대 글자수 (기본 2000)

    Returns:
        {
            'parts': [{'content': str, 'char_count': int, 'part_number': int}],
            'total_parts': int,
        }
    """
    if not content or not content.strip():
        return {'parts': [], 'total_parts': 0}

    max_chars = max(500, min(10000, max_chars))
    text = content.strip()

    if len(text) <= max_chars:
        return {
            'parts': [{'content': text, 'char_count': len(text), 'part_number': 1}],
            'total_parts': 1,
        }

    paragraphs = text.split('\n\n')
    parts: List[dict] = []
    current_chunk: List[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = len(para) + 2  # \n\n
        if current_len + para_len > max_chars and current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            parts.append({
                'content': chunk_text,
                'char_count': len(chunk_text),
                'part_number': len(parts) + 1,
            })
            current_chunk = [para]
            current_len = para_len
        else:
            current_chunk.append(para)
            current_len += para_len

    # 마지막 청크
    if current_chunk:
        chunk_text = '\n\n'.join(current_chunk)
        parts.append({
            'content': chunk_text,
            'char_count': len(chunk_text),
            'part_number': len(parts) + 1,
        })

    return {
        'parts': parts,
        'total_parts': len(parts),
    }


def _make_part(title: str, body: str, part_number: int) -> dict:
    """파트 객체를 생성합니다."""
    full_content = f'# {title}\n\n{body}'.strip() if title else body
    return {
        'title': title or f'파트 {part_number}',
        'content': full_content,
        'word_count': len(_WORD_PATTERN.findall(full_content)),
        'part_number': part_number,
    }
