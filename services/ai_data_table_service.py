"""AI 데이터 테이블 서비스

비정형 텍스트에서 구조화된 테이블을 추출하고,
필터링·정렬·집계·CSV 내보내기 기능을 제공합니다.
"""
import re
import csv
import io
import uuid
from dataclasses import dataclass, field


@dataclass
class TableColumn:
    """테이블 컬럼 정의"""
    name: str                           # 컬럼명
    data_type: str                      # text / number / date / boolean
    description: str                    # 컬럼 설명


@dataclass
class TableRow:
    """테이블 행"""
    row_id: str                         # 행 고유 ID
    values: dict[str, str]              # {컬럼명: 값}


@dataclass
class DataTable:
    """구조화된 데이터 테이블"""
    table_id: str                       # 테이블 고유 ID
    title: str                          # 테이블 제목
    columns: list[TableColumn] = field(default_factory=list)
    rows: list[TableRow] = field(default_factory=list)


# ── key: value 패턴 ──────────────────────────────────────────
_KV_PATTERN = re.compile(r'^(.+?)\s*[:：]\s*(.+)$', re.MULTILINE)

# ── 테이블 구분선 패턴 (마크다운 등) ─────────────────────────
_TABLE_SEP_PATTERN = re.compile(r'^\|?[\s\-:]+\|', re.MULTILINE)

# ── 파이프 구분 행 패턴 ──────────────────────────────────────
_PIPE_ROW_PATTERN = re.compile(r'^\|(.+)\|$', re.MULTILINE)

# ── 날짜 패턴 ────────────────────────────────────────────────
_DATE_PATTERN = re.compile(r'^\d{4}[-/]\d{1,2}[-/]\d{1,2}$')

# ── 숫자 패턴 (정수, 소수, 음수, 쉼표 포함) ─────────────────
_NUMBER_PATTERN = re.compile(r'^-?[\d,]+\.?\d*$')

# ── 불리언 패턴 ──────────────────────────────────────────────
_BOOL_VALUES = {'true', 'false', 'yes', 'no', '예', '아니오', '참', '거짓'}


def _infer_data_type(value: str) -> str:
    """값으로부터 데이터 타입 추론"""
    v = value.strip().lower()
    if v in _BOOL_VALUES:
        return 'boolean'
    if _DATE_PATTERN.match(v):
        return 'date'
    if _NUMBER_PATTERN.match(v.replace(',', '')):
        return 'number'
    return 'text'


def _parse_number(value: str) -> float:
    """문자열을 숫자로 변환 (쉼표 제거)"""
    cleaned = value.strip().replace(',', '')
    return float(cleaned)


def _extract_pipe_table(text: str) -> DataTable | None:
    """마크다운 파이프 테이블 파싱"""
    rows = _PIPE_ROW_PATTERN.findall(text)
    if len(rows) < 2:
        return None

    # 헤더 추출
    headers = [h.strip() for h in rows[0].split('|') if h.strip()]
    if not headers:
        return None

    # 구분선 건너뛰기
    data_start = 1
    for i, row_text in enumerate(rows[1:], 1):
        cells = [c.strip() for c in row_text.split('|') if c.strip()]
        if all(re.match(r'^[-:]+$', c) for c in cells):
            data_start = i + 1
            break

    # 데이터 행 파싱
    data_rows_raw = rows[data_start:] if data_start < len(rows) else rows[1:]

    # 타입 추론 (첫 번째 데이터 행 기준)
    columns = []
    if data_rows_raw:
        first_cells = [c.strip() for c in data_rows_raw[0].split('|') if c.strip()]
        for i, name in enumerate(headers):
            sample = first_cells[i] if i < len(first_cells) else ''
            dtype = _infer_data_type(sample)
            columns.append(TableColumn(name=name, data_type=dtype, description=f'{name} 컬럼'))
    else:
        columns = [TableColumn(name=h, data_type='text', description=f'{h} 컬럼') for h in headers]

    parsed_rows = []
    for row_text in data_rows_raw:
        cells = [c.strip() for c in row_text.split('|') if c.strip()]
        # 구분선 행 건너뛰기
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        values = {}
        for i, col in enumerate(columns):
            values[col.name] = cells[i] if i < len(cells) else ''
        parsed_rows.append(TableRow(row_id=uuid.uuid4().hex[:8], values=values))

    if not parsed_rows:
        return None

    return DataTable(
        table_id=uuid.uuid4().hex[:8],
        title='추출된 테이블',
        columns=columns,
        rows=parsed_rows,
    )


def _extract_kv_table(text: str, hint: str) -> DataTable | None:
    """key: value 패턴에서 테이블 추출"""
    matches = _KV_PATTERN.findall(text)
    if len(matches) < 2:
        return None

    # 그룹화: 빈 줄 기준으로 레코드 분리
    lines = text.strip().split('\n')
    records: list[dict[str, str]] = []
    current: dict[str, str] = {}

    for line in lines:
        line = line.strip()
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        m = re.match(r'^(.+?)\s*[:：]\s*(.+)$', line)
        if m:
            current[m.group(1).strip()] = m.group(2).strip()

    if current:
        records.append(current)

    # 레코드가 1개이면 단일 레코드 테이블
    if not records:
        return None

    # 모든 키 수집 (순서 유지)
    all_keys: list[str] = []
    seen: set[str] = set()
    for rec in records:
        for k in rec:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    # 타입 추론
    columns = []
    for key in all_keys:
        sample = ''
        for rec in records:
            if key in rec:
                sample = rec[key]
                break
        dtype = _infer_data_type(sample)
        columns.append(TableColumn(name=key, data_type=dtype, description=f'{key} 컬럼'))

    rows = []
    for rec in records:
        values = {col.name: rec.get(col.name, '') for col in columns}
        rows.append(TableRow(row_id=uuid.uuid4().hex[:8], values=values))

    title = hint if hint else '추출된 테이블'
    return DataTable(
        table_id=uuid.uuid4().hex[:8],
        title=title,
        columns=columns,
        rows=rows,
    )


def extract_table(text: str, hint: str = '') -> DataTable:
    """텍스트에서 구조화된 테이블 추출

    Args:
        text: 비정형 텍스트
        hint: 테이블 제목 힌트

    Returns:
        추출된 DataTable (추출 실패 시 빈 테이블)
    """
    if not text or not text.strip():
        return DataTable(
            table_id=uuid.uuid4().hex[:8],
            title=hint or '빈 테이블',
            columns=[],
            rows=[],
        )

    # 1) 파이프 테이블 시도
    result = _extract_pipe_table(text)
    if result:
        if hint:
            result.title = hint
        return result

    # 2) key:value 패턴 시도
    result = _extract_kv_table(text, hint)
    if result:
        return result

    # 3) 실패 시 빈 테이블
    return DataTable(
        table_id=uuid.uuid4().hex[:8],
        title=hint or '추출 실패',
        columns=[],
        rows=[],
    )


def filter_rows(table: DataTable, column: str, operator: str, value: str) -> DataTable:
    """테이블 행 필터링

    Args:
        table: 대상 테이블
        column: 필터 컬럼명
        operator: eq / contains / gt / lt
        value: 비교 값

    Returns:
        필터링된 새 DataTable
    """
    filtered = []
    for row in table.rows:
        cell = row.values.get(column, '')
        match = False

        if operator == 'eq':
            match = cell.strip().lower() == value.strip().lower()
        elif operator == 'contains':
            match = value.strip().lower() in cell.strip().lower()
        elif operator == 'gt':
            try:
                match = _parse_number(cell) > _parse_number(value)
            except (ValueError, TypeError):
                match = cell > value
        elif operator == 'lt':
            try:
                match = _parse_number(cell) < _parse_number(value)
            except (ValueError, TypeError):
                match = cell < value

        if match:
            filtered.append(row)

    return DataTable(
        table_id=table.table_id,
        title=table.title,
        columns=list(table.columns),
        rows=filtered,
    )


def sort_table(table: DataTable, column: str, ascending: bool = True) -> DataTable:
    """테이블 정렬

    Args:
        table: 대상 테이블
        column: 정렬 컬럼명
        ascending: 오름차순 여부

    Returns:
        정렬된 새 DataTable
    """
    # 컬럼 타입 확인
    col_type = 'text'
    for col in table.columns:
        if col.name == column:
            col_type = col.data_type
            break

    def sort_key(row: TableRow):
        val = row.values.get(column, '')
        if col_type == 'number':
            try:
                return _parse_number(val)
            except (ValueError, TypeError):
                return float('inf') if ascending else float('-inf')
        return val.lower()

    sorted_rows = sorted(table.rows, key=sort_key, reverse=not ascending)

    return DataTable(
        table_id=table.table_id,
        title=table.title,
        columns=list(table.columns),
        rows=sorted_rows,
    )


def aggregate(table: DataTable, column: str, func: str) -> float | str:
    """테이블 집계

    Args:
        table: 대상 테이블
        column: 집계 컬럼명
        func: count / sum / avg / min / max

    Returns:
        집계 결과
    """
    values = [row.values.get(column, '') for row in table.rows]

    if func == 'count':
        return float(len(values))

    # 숫자 변환
    numbers = []
    for v in values:
        try:
            numbers.append(_parse_number(v))
        except (ValueError, TypeError):
            continue

    if not numbers:
        if func in ('sum', 'avg'):
            return 0.0
        if func == 'min':
            return min(values) if values else ''
        if func == 'max':
            return max(values) if values else ''
        return 0.0

    if func == 'sum':
        return sum(numbers)
    elif func == 'avg':
        return sum(numbers) / len(numbers)
    elif func == 'min':
        return min(numbers)
    elif func == 'max':
        return max(numbers)

    return 0.0


def export_csv(table: DataTable) -> str:
    """테이블을 CSV 문자열로 내보내기

    Args:
        table: 대상 테이블

    Returns:
        CSV 형식 문자열
    """
    output = io.StringIO()
    col_names = [col.name for col in table.columns]

    writer = csv.writer(output)
    writer.writerow(col_names)

    for row in table.rows:
        writer.writerow([row.values.get(name, '') for name in col_names])

    return output.getvalue()
