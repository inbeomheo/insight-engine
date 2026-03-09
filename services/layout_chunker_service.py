"""
구조 인지형 문서 청킹 서비스.

마크다운 문서를 표/슬라이드/헤딩/코드블록/리스트 등 구조 단위로 분리하여
레이아웃 정보를 보존한 청크 리스트를 반환한다.
"""

import re
import uuid
from dataclasses import dataclass, field


@dataclass
class LayoutChunk:
    """구조 보존 청크 단위."""
    chunk_id: str
    content: str
    chunk_type: str          # "heading", "paragraph", "table", "list", "code_block"
    heading: str             # 속한 섹션의 헤딩 텍스트 (없으면 빈 문자열)
    position: int            # 문서 내 순서 (0-based)
    metadata: dict = field(default_factory=dict)


# ── 내부 상수 ────────────────────────────────────────────

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$')
_TABLE_ROW_RE = re.compile(r'^\|.+\|$')
_TABLE_SEP_RE = re.compile(r'^\|[\s:|-]+\|$')
_CODE_FENCE_RE = re.compile(r'^(`{3,}|~{3,})')
_ORDERED_LIST_RE = re.compile(r'^\d+\.\s+')
_UNORDERED_LIST_RE = re.compile(r'^[-*+]\s+')


def _make_id() -> str:
    return uuid.uuid4().hex[:12]


def _split_large_chunk(text: str, max_size: int) -> list[str]:
    """max_size를 초과하는 텍스트를 줄 단위로 분할. 단일 줄이 초과하면 강제 절단."""
    if len(text) <= max_size:
        return [text]

    parts: list[str] = []
    current_lines: list[str] = []
    current_len = 0

    for line in text.split('\n'):
        line_len = len(line) + 1  # 개행 포함
        if current_len + line_len > max_size and current_lines:
            parts.append('\n'.join(current_lines))
            current_lines = []
            current_len = 0
        current_lines.append(line)
        current_len += line_len

    if current_lines:
        parts.append('\n'.join(current_lines))

    # 단일 줄이 max_size 초과하면 강제 절단
    result: list[str] = []
    for part in parts:
        if len(part) <= max_size:
            result.append(part)
        else:
            for i in range(0, len(part), max_size):
                result.append(part[i:i + max_size])

    return result


def _detect_list_line(line: str) -> bool:
    """리스트 항목인지 판별."""
    return bool(_ORDERED_LIST_RE.match(line) or _UNORDERED_LIST_RE.match(line))


def chunk_with_layout(
    document: str,
    doc_type: str = 'markdown',
    max_chunk_size: int = 500,
) -> list[LayoutChunk]:
    """
    마크다운 문서를 구조 단위로 청킹한다.

    Args:
        document: 원본 문서 텍스트.
        doc_type: 문서 형식 (현재 'markdown'만 지원).
        max_chunk_size: 청크 최대 문자 수. 초과 시 줄 단위로 분할.

    Returns:
        LayoutChunk 리스트. 빈 문서이면 빈 리스트.
    """
    if not document or not document.strip():
        return []

    lines = document.split('\n')
    raw_blocks = _parse_blocks(lines)

    # 청크 생성 + 크기 제한 적용
    chunks: list[LayoutChunk] = []
    position = 0
    current_heading = ''

    for block_type, block_content, block_meta in raw_blocks:
        # 헤딩이면 현재 섹션 헤딩 갱신
        if block_type == 'heading':
            current_heading = block_meta.get('heading_text', '')

        text = block_content.strip()
        if not text:
            continue

        parts = _split_large_chunk(text, max_chunk_size)
        for part in parts:
            chunk = LayoutChunk(
                chunk_id=_make_id(),
                content=part,
                chunk_type=block_type,
                heading=current_heading,
                position=position,
                metadata=dict(block_meta),
            )
            chunks.append(chunk)
            position += 1

    return chunks


def _parse_blocks(lines: list[str]) -> list[tuple[str, str, dict]]:
    """
    줄 목록을 (block_type, content, metadata) 블록으로 분류.

    반환 블록 타입: heading, paragraph, table, list, code_block
    """
    blocks: list[tuple[str, str, dict]] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # ── 코드 블록 ────────────────────────────
        fence_match = _CODE_FENCE_RE.match(line.strip())
        if fence_match:
            fence_marker = fence_match.group(1)
            fence_char = fence_marker[0]
            fence_len = len(fence_marker)
            code_lines = [line]
            i += 1
            while i < n:
                close_match = _CODE_FENCE_RE.match(lines[i].strip())
                if close_match and close_match.group(1)[0] == fence_char and len(close_match.group(1)) >= fence_len:
                    code_lines.append(lines[i])
                    i += 1
                    break
                code_lines.append(lines[i])
                i += 1
            # 언어 정보 추출
            lang = line.strip()[fence_len:].strip()
            meta = {'language': lang} if lang else {}
            blocks.append(('code_block', '\n'.join(code_lines), meta))
            continue

        # ── 헤딩 ─────────────────────────────────
        heading_match = _HEADING_RE.match(line.strip())
        if heading_match:
            level = len(heading_match.group(1))
            text = heading_match.group(2).strip()
            blocks.append(('heading', line, {
                'heading_text': text,
                'heading_level': level,
            }))
            i += 1
            continue

        # ── 표 ───────────────────────────────────
        stripped = line.strip()
        if _TABLE_ROW_RE.match(stripped):
            table_lines = [line]
            i += 1
            while i < n and _TABLE_ROW_RE.match(lines[i].strip()):
                table_lines.append(lines[i])
                i += 1
            # 행/열 수 메타데이터
            data_rows = [l for l in table_lines if not _TABLE_SEP_RE.match(l.strip())]
            col_count = len(table_lines[0].strip().split('|')) - 2 if table_lines else 0
            blocks.append(('table', '\n'.join(table_lines), {
                'row_count': len(data_rows),
                'col_count': max(col_count, 0),
            }))
            continue

        # ── 리스트 ───────────────────────────────
        if _detect_list_line(stripped):
            list_lines = [line]
            i += 1
            while i < n:
                next_stripped = lines[i].strip()
                # 리스트 항목이거나 들여쓰기된 연속 줄
                if _detect_list_line(next_stripped) or (next_stripped and lines[i].startswith(('  ', '\t'))):
                    list_lines.append(lines[i])
                    i += 1
                elif next_stripped == '':
                    # 빈 줄 다음에 리스트가 이어지면 계속
                    if i + 1 < n and _detect_list_line(lines[i + 1].strip()):
                        list_lines.append(lines[i])
                        i += 1
                    else:
                        break
                else:
                    break
            item_count = sum(1 for l in list_lines if _detect_list_line(l.strip()))
            blocks.append(('list', '\n'.join(list_lines), {
                'item_count': item_count,
            }))
            continue

        # ── 빈 줄 → 건너뜀 ──────────────────────
        if not stripped:
            i += 1
            continue

        # ── 일반 단락 ────────────────────────────
        para_lines = [line]
        i += 1
        while i < n:
            next_line = lines[i]
            next_stripped = next_line.strip()
            # 빈 줄, 헤딩, 표, 코드펜스, 리스트 시작이면 단락 종료
            if (not next_stripped
                    or _HEADING_RE.match(next_stripped)
                    or _TABLE_ROW_RE.match(next_stripped)
                    or _CODE_FENCE_RE.match(next_stripped)
                    or _detect_list_line(next_stripped)):
                break
            para_lines.append(next_line)
            i += 1

        blocks.append(('paragraph', '\n'.join(para_lines), {}))

    return blocks
