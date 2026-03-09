"""
CSV 데이터 × 템플릿 대량 콘텐츠 생성 오케스트레이션 서비스

CSV 행마다 {{변수명}} 치환으로 콘텐츠를 일괄 생성.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class OrchestrationResult:
    """단일 행의 생성 결과."""
    row_index: int
    input_data: dict
    output: str
    status: str          # "success" | "error"
    error: Optional[str]


# 템플릿 변수 패턴: {{변수명}}
_VAR_PATTERN = re.compile(r'\{\{(\w+)\}\}')


def _extract_template_vars(template: str) -> List[str]:
    """템플릿에서 모든 변수명을 추출합니다."""
    return list(set(_VAR_PATTERN.findall(template)))


def _render_template(template: str, data: dict) -> str:
    """템플릿의 {{변수명}}을 data 값으로 치환합니다.

    모든 변수가 data에 존재해야 합니다.

    Args:
        template: {{변수명}} 포함 템플릿 문자열
        data: 변수명 → 값 매핑

    Returns:
        치환된 문자열

    Raises:
        KeyError: 누락 변수가 있을 때
    """
    required_vars = _extract_template_vars(template)
    missing = [v for v in required_vars if v not in data]
    if missing:
        raise KeyError(f"누락 변수: {', '.join(missing)}")

    def replacer(match):
        key = match.group(1)
        return str(data[key])

    return _VAR_PATTERN.sub(replacer, template)


def orchestrate_bulk(csv_data: List[dict], template: str) -> List[OrchestrationResult]:
    """CSV 데이터 × 템플릿으로 대량 콘텐츠를 생성합니다.

    각 행의 dict 키가 템플릿 {{변수명}}과 매핑됩니다.
    누락 변수가 있으면 해당 행은 status="error"로 처리됩니다.

    Args:
        csv_data: dict 리스트 (각 행이 하나의 dict)
        template: {{변수명}} 포함 템플릿 문자열

    Returns:
        OrchestrationResult 리스트 (입력 순서 보장)
    """
    if not csv_data:
        return []

    if not template or not template.strip():
        return [
            OrchestrationResult(
                row_index=i,
                input_data=row,
                output="",
                status="error",
                error="빈 템플릿",
            )
            for i, row in enumerate(csv_data)
        ]

    results = []
    for i, row in enumerate(csv_data):
        try:
            rendered = _render_template(template, row)
            results.append(OrchestrationResult(
                row_index=i,
                input_data=row,
                output=rendered,
                status="success",
                error=None,
            ))
        except KeyError as e:
            results.append(OrchestrationResult(
                row_index=i,
                input_data=row,
                output="",
                status="error",
                error=str(e),
            ))

    return results


def get_template_vars(template: str) -> List[str]:
    """템플릿에서 필요한 변수 목록을 반환합니다.

    Args:
        template: {{변수명}} 포함 템플릿

    Returns:
        변수명 리스트 (중복 제거, 정렬)
    """
    return sorted(_extract_template_vars(template))


def validate_csv_data(csv_data: List[dict], template: str) -> Dict:
    """CSV 데이터가 템플릿과 호환되는지 검증합니다.

    Args:
        csv_data: dict 리스트
        template: {{변수명}} 포함 템플릿

    Returns:
        검증 결과 dict: valid, total_rows, valid_rows, invalid_rows, missing_vars_per_row
    """
    required_vars = set(_extract_template_vars(template))
    valid_rows = 0
    invalid_rows = 0
    missing_per_row = {}

    for i, row in enumerate(csv_data):
        missing = required_vars - set(row.keys())
        if missing:
            invalid_rows += 1
            missing_per_row[i] = sorted(missing)
        else:
            valid_rows += 1

    return {
        'valid': invalid_rows == 0,
        'total_rows': len(csv_data),
        'valid_rows': valid_rows,
        'invalid_rows': invalid_rows,
        'missing_vars_per_row': missing_per_row,
    }
