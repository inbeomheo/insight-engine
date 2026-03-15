#!/usr/bin/env python3
"""agent-browser 출력에서 메트릭을 수집합니다. (Frozen — 수정 금지)"""

import json
import sys
from typing import Dict


def collect_from_snapshot(snapshot_text: str) -> Dict:
    """DOM 스냅샷에서 접근성 메트릭을 수집합니다."""
    lines = snapshot_text.strip().split('\n')
    total_elements = len(lines)
    interactive = sum(1 for l in lines if any(k in l.lower() for k in ['button', 'input', 'link', 'select', 'textarea']))
    has_landmarks = any(k in snapshot_text.lower() for k in ['navigation', 'main', 'banner', 'contentinfo'])

    return {
        'total_elements': total_elements,
        'interactive_elements': interactive,
        'has_landmarks': has_landmarks,
        'dom_score': min(100, (interactive / max(total_elements, 1)) * 200 + (30 if has_landmarks else 0))
    }


def collect_from_console(console_text: str) -> Dict:
    """콘솔 출력에서 에러/경고를 수집합니다."""
    lines = console_text.strip().split('\n') if console_text.strip() else []
    errors = sum(1 for l in lines if 'error' in l.lower())
    warnings = sum(1 for l in lines if 'warning' in l.lower() or 'warn' in l.lower())

    error_score = max(0, 100 - errors * 20 - warnings * 5)

    return {
        'errors': errors,
        'warnings': warnings,
        'error_score': error_score
    }


def collect_form_result(success: bool) -> Dict:
    """폼 테스트 결과를 수집합니다."""
    return {
        'form_success': success,
        'form_score': 100 if success else 0
    }


def collect_visual_check(screenshot_exists: bool, layout_ok: bool) -> Dict:
    """시각 검증 결과를 수집합니다."""
    score = 0
    if screenshot_exists:
        score += 50
    if layout_ok:
        score += 50
    return {
        'screenshot_exists': screenshot_exists,
        'layout_ok': layout_ok,
        'visual_score': score
    }


if __name__ == '__main__':
    # 테스트용 더미 실행
    print(json.dumps({
        'error': collect_from_console(''),
        'dom': collect_from_snapshot('button\ninput\nlink\nmain'),
        'form': collect_form_result(True),
        'visual': collect_visual_check(True, True)
    }, indent=2))
