"""
콘텐츠 병합(Merge) 서비스

여러 생성 결과를 하나의 통합 문서로 병합합니다.
섹션 결합, 중복 제거, 목차 자동 생성을 규칙 기반으로 처리.
"""
import hashlib
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
_DUPLICATE_THRESHOLD = 0.85


def _normalize_text(text: str) -> str:
    """비교를 위한 텍스트 정규화."""
    return re.sub(r'\s+', ' ', text.lower().strip())


def _sentence_hash(sentence: str) -> str:
    """문장 해시를 생성합니다 (중복 탐지용)."""
    normalized = _normalize_text(sentence)
    return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:12]


def _extract_sections(content: str) -> List[dict]:
    """마크다운 콘텐츠를 섹션별로 분리합니다."""
    lines = content.split('\n')
    sections = []
    current_heading = ''
    current_level = 0
    current_body = []

    for line in lines:
        match = _HEADING_PATTERN.match(line)
        if match:
            # 이전 섹션 저장
            if current_heading or current_body:
                sections.append({
                    'heading': current_heading,
                    'level': current_level,
                    'body': '\n'.join(current_body).strip(),
                })
            current_heading = match.group(2)
            current_level = len(match.group(1))
            current_body = []
        else:
            current_body.append(line)

    # 마지막 섹션
    if current_heading or current_body:
        sections.append({
            'heading': current_heading,
            'level': current_level,
            'body': '\n'.join(current_body).strip(),
        })

    return sections


def _deduplicate_sentences(text: str) -> str:
    """문장 수준 중복을 제거합니다."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    seen_hashes = set()
    unique = []
    for sent in sentences:
        if not sent.strip():
            continue
        h = _sentence_hash(sent)
        if h not in seen_hashes:
            seen_hashes.add(h)
            unique.append(sent)
    return ' '.join(unique)


def merge_contents(contents: List[dict], deduplicate: bool = True) -> dict:
    """여러 콘텐츠를 하나로 병합합니다.

    Args:
        contents: [{'title': str, 'content': str, 'source': str(optional)}, ...]
        deduplicate: 문장 수준 중복 제거 여부

    Returns:
        {
            'merged_content': str,
            'toc': [{'heading': str, 'level': int}],
            'source_count': int,
            'section_count': int,
            'char_count': int,
            'duplicate_sentences_removed': int,
        }
    """
    if not contents:
        return {
            'merged_content': '',
            'toc': [],
            'source_count': 0,
            'section_count': 0,
            'char_count': 0,
            'duplicate_sentences_removed': 0,
        }

    all_sections = []
    seen_heading_hashes = set()
    duplicates_removed = 0

    for idx, item in enumerate(contents):
        content = item.get('content', '')
        title = item.get('title', f'소스 {idx + 1}')
        source = item.get('source', '')

        if not content or not content.strip():
            continue

        sections = _extract_sections(content)
        for section in sections:
            heading_hash = _sentence_hash(section['heading']) if section['heading'] else ''

            # 같은 제목의 섹션이 이미 있으면 본문만 병합
            if heading_hash and heading_hash in seen_heading_hashes:
                # 기존 섹션 찾아서 본문 추가
                for existing in all_sections:
                    if _sentence_hash(existing['heading']) == heading_hash:
                        existing['body'] += '\n\n' + section['body']
                        break
                continue

            if heading_hash:
                seen_heading_hashes.add(heading_hash)
            all_sections.append(section)

    # 병합된 마크다운 생성
    merged_parts = []
    toc = []

    for section in all_sections:
        if section['heading']:
            prefix = '#' * max(1, section['level'])
            merged_parts.append(f"{prefix} {section['heading']}")
            toc.append({'heading': section['heading'], 'level': section['level']})

        body = section['body']
        if deduplicate and body:
            original_sentences = len(re.split(r'(?<=[.!?])\s+', body))
            body = _deduplicate_sentences(body)
            deduped_sentences = len(re.split(r'(?<=[.!?])\s+', body))
            duplicates_removed += max(0, original_sentences - deduped_sentences)

        if body:
            merged_parts.append(body)
        merged_parts.append('')  # 빈 줄 구분

    merged_content = '\n'.join(merged_parts).strip()

    return {
        'merged_content': merged_content,
        'toc': toc,
        'source_count': len(contents),
        'section_count': len(all_sections),
        'char_count': len(merged_content),
        'duplicate_sentences_removed': duplicates_removed,
    }
