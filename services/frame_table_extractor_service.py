"""
프레임 테이블 추출 서비스
영상 프레임 설명에서 표(table) 구조 데이터를 파싱한다.
파이프(|) 구분 텍스트, 탭 구분, 콤마 구분 등을 지원.
"""
import logging
import re
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class ExtractedTable:
    """추출된 테이블"""
    table_id: str
    video_id: str
    timestamp: str
    headers: List[str]
    rows: List[List[str]]
    confidence: float  # 0.0 ~ 1.0


def _validate_timestamp(ts: str) -> bool:
    """MM:SS 또는 HH:MM:SS 형식 검증"""
    return bool(re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', ts))


def _parse_pipe_table(text: str) -> Optional[Dict]:
    """파이프(|) 구분 표를 파싱

    형식:
    | Header1 | Header2 |
    |---------|---------|
    | Cell1   | Cell2   |

    또는 구분선 없이:
    | Header1 | Header2 |
    | Cell1   | Cell2   |
    """
    lines = [ln.strip() for ln in text.strip().split('\n') if ln.strip()]
    if len(lines) < 2:
        return None

    pipe_lines = []
    for line in lines:
        if '|' in line:
            pipe_lines.append(line)

    if len(pipe_lines) < 2:
        return None

    def split_cells(line: str) -> List[str]:
        """파이프로 셀 분리"""
        line = line.strip()
        if line.startswith('|'):
            line = line[1:]
        if line.endswith('|'):
            line = line[:-1]
        return [cell.strip() for cell in line.split('|')]

    # 구분선 제거 (---로 구성된 행)
    data_lines = []
    for line in pipe_lines:
        cells = split_cells(line)
        if all(re.match(r'^[-:]+$', c) for c in cells if c):
            continue
        data_lines.append(cells)

    if len(data_lines) < 2:
        return None

    headers = data_lines[0]
    rows = data_lines[1:]

    # 컬럼 수 통일
    col_count = len(headers)
    normalized_rows = []
    for row in rows:
        if len(row) < col_count:
            row.extend([''] * (col_count - len(row)))
        elif len(row) > col_count:
            row = row[:col_count]
        normalized_rows.append(row)

    return {"headers": headers, "rows": normalized_rows, "confidence": 0.9}


def _parse_tab_table(text: str) -> Optional[Dict]:
    """탭 구분 표를 파싱"""
    lines = [ln for ln in text.strip().split('\n') if ln.strip()]
    if len(lines) < 2:
        return None

    # 탭이 포함된 행이 2개 이상이어야 함
    tab_lines = [ln for ln in lines if '\t' in ln]
    if len(tab_lines) < 2:
        return None

    headers = [c.strip() for c in tab_lines[0].split('\t')]
    rows = []
    for line in tab_lines[1:]:
        cells = [c.strip() for c in line.split('\t')]
        # 컬럼 수 맞추기
        if len(cells) < len(headers):
            cells.extend([''] * (len(headers) - len(cells)))
        elif len(cells) > len(headers):
            cells = cells[:len(headers)]
        rows.append(cells)

    if not rows:
        return None

    return {"headers": headers, "rows": rows, "confidence": 0.7}


def _parse_csv_like(text: str) -> Optional[Dict]:
    """콤마 구분 표를 파싱 (최소 2열, 2행)"""
    lines = [ln.strip() for ln in text.strip().split('\n') if ln.strip()]
    if len(lines) < 2:
        return None

    # 콤마가 포함된 행이 2개 이상이어야 함
    csv_lines = [ln for ln in lines if ',' in ln]
    if len(csv_lines) < 2:
        return None

    headers = [c.strip() for c in csv_lines[0].split(',')]
    if len(headers) < 2:
        return None

    rows = []
    for line in csv_lines[1:]:
        cells = [c.strip() for c in line.split(',')]
        if len(cells) < len(headers):
            cells.extend([''] * (len(headers) - len(cells)))
        elif len(cells) > len(headers):
            cells = cells[:len(headers)]
        rows.append(cells)

    if not rows:
        return None

    return {"headers": headers, "rows": rows, "confidence": 0.5}


def _try_parse_table(text: str) -> Optional[Dict]:
    """여러 파서를 순서대로 시도"""
    # 우선순위: 파이프 > 탭 > 콤마
    for parser in [_parse_pipe_table, _parse_tab_table, _parse_csv_like]:
        result = parser(text)
        if result:
            return result
    return None


def extract_tables_from_frames(
    video_id: str,
    frame_descriptions: Optional[List[Dict]] = None,
) -> List[ExtractedTable]:
    """프레임 설명에서 테이블 구조를 추출한다.

    Args:
        video_id: YouTube 영상 ID
        frame_descriptions: 프레임 설명 목록
            [{"timestamp": "02:00", "content": "표 데이터..."}]

    Returns:
        ExtractedTable 리스트
    """
    if not video_id or not video_id.strip():
        logger.warning("video_id가 비어 있습니다")
        return []

    if not frame_descriptions:
        logger.info("프레임 설명이 없어 빈 리스트를 반환합니다")
        return []

    video_id = video_id.strip()
    results: List[ExtractedTable] = []

    for idx, frame in enumerate(frame_descriptions):
        if not isinstance(frame, dict):
            logger.warning("프레임 #%d: dict가 아닌 값 무시", idx)
            continue

        ts = frame.get("timestamp", "")
        content = frame.get("content", "")

        if not ts or not _validate_timestamp(str(ts)):
            logger.warning("프레임 #%d: 유효하지 않은 타임스탬프 '%s'", idx, ts)
            continue

        if not content or not content.strip():
            continue

        parsed = _try_parse_table(content)
        if not parsed:
            continue

        # 빈 헤더 필터링
        headers = [h for h in parsed["headers"] if h]
        if not headers:
            continue

        table = ExtractedTable(
            table_id=str(uuid.uuid4()),
            video_id=video_id,
            timestamp=str(ts),
            headers=parsed["headers"],
            rows=parsed["rows"],
            confidence=parsed["confidence"],
        )
        results.append(table)

    logger.info(
        "video_id=%s: %d개 프레임에서 %d개 테이블 추출",
        video_id, len(frame_descriptions), len(results),
    )
    return results
