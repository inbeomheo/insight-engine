"""
데이터셋 추출 서비스 — 콘텐츠에서 구조화된 데이터셋 추출
"""

import re
import uuid
from dataclasses import dataclass, field


@dataclass
class ExtractedField:
    """추출된 필드"""
    field_name: str
    field_type: str  # text / number / date / category
    values: list


@dataclass
class ExtractedDataset:
    """추출된 데이터셋"""
    dataset_id: str
    source: str
    fields: list[ExtractedField]
    row_count: int


def extract_from_text(text: str, field_hints: list[str]) -> ExtractedDataset:
    """텍스트에서 키-값 패턴 추출"""
    fields: dict[str, list] = {hint: [] for hint in field_hints}

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # "키: 값" 또는 "키 = 값" 패턴 매칭
        for hint in field_hints:
            patterns = [
                rf'{re.escape(hint)}\s*[:=]\s*(.+)',
                rf'{re.escape(hint)}\s+(.+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    value = match.group(1).strip()
                    fields[hint].append(value)
                    break

    extracted_fields = []
    max_rows = 0

    for name, values in fields.items():
        if values:
            ftype = detect_field_types(values)
            extracted_fields.append(ExtractedField(
                field_name=name,
                field_type=ftype,
                values=values
            ))
            max_rows = max(max_rows, len(values))

    return ExtractedDataset(
        dataset_id=str(uuid.uuid4())[:8],
        source=text[:100],
        fields=extracted_fields,
        row_count=max_rows
    )


def detect_field_types(values: list) -> str:
    """값 목록에서 타입 추론"""
    if not values:
        return 'text'

    # 숫자 체크
    number_count = 0
    for v in values:
        try:
            float(str(v).replace(',', ''))
            number_count += 1
        except (ValueError, TypeError):
            pass

    if number_count == len(values):
        return 'number'

    # 날짜 체크
    date_patterns = [
        r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
        r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',
    ]
    date_count = 0
    for v in values:
        for pattern in date_patterns:
            if re.match(pattern, str(v).strip()):
                date_count += 1
                break

    if date_count == len(values):
        return 'date'

    # 카테고리 체크: 고유값이 전체의 50% 미만이면 카테고리
    unique = set(str(v).strip().lower() for v in values)
    if len(unique) < len(values) * 0.5 and len(values) >= 4:
        return 'category'

    return 'text'


def validate_dataset(dataset: ExtractedDataset) -> list[str]:
    """데이터 검증 — 빈 값, 타입 불일치"""
    errors = []

    for field in dataset.fields:
        # 빈 값 체크
        empty_count = sum(1 for v in field.values if not str(v).strip())
        if empty_count > 0:
            errors.append(f"'{field.field_name}': {empty_count}개의 빈 값이 있습니다.")

        # 타입 불일치 체크
        if field.field_type == 'number':
            for v in field.values:
                try:
                    float(str(v).replace(',', ''))
                except (ValueError, TypeError):
                    errors.append(f"'{field.field_name}': 숫자가 아닌 값 '{v}'이 있습니다.")
                    break

    if not dataset.fields:
        errors.append('추출된 필드가 없습니다.')

    return errors


def export_as_csv(dataset: ExtractedDataset) -> str:
    """CSV 내보내기"""
    if not dataset.fields:
        return ''

    # 헤더
    headers = [f.field_name for f in dataset.fields]
    lines = [','.join(headers)]

    # 행
    for i in range(dataset.row_count):
        row = []
        for field in dataset.fields:
            if i < len(field.values):
                val = str(field.values[i]).replace('"', '""')
                row.append(f'"{val}"')
            else:
                row.append('""')
        lines.append(','.join(row))

    return '\n'.join(lines)
