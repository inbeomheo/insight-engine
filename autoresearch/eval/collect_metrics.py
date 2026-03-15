#!/usr/bin/env python3
"""agent-browser CLI 기반 메트릭 수집. (Frozen — 수정 금지)

agent-browser(Vercel) CLI를 사용하여 실제 렌더링된 화면에서 메트릭을 수집한다.
- snapshot: 접근성 트리 (DOM 구조, aria, landmark)
- get box: 요소 바운딩 박스 (레이아웃 위치/크기)
- get styles: 계산된 CSS 값 (폰트, 색상, 간격)
- screenshot --annotate: 주석 스크린샷 (시각 비교)
- console: 콘솔 에러/경고
"""

import json
import subprocess
import sys
from typing import Dict, Optional


def _run_ab(args: list[str], json_output: bool = False) -> str:
    """agent-browser CLI 명령을 실행합니다."""
    cmd = ['agent-browser'] + args
    if json_output:
        cmd.append('--json')
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    return result.stdout.strip()


def collect_from_snapshot(snapshot_text: str) -> Dict:
    """DOM 스냅샷에서 접근성 메트릭을 수집합니다."""
    lines = snapshot_text.strip().split('\n')
    total_elements = len(lines)
    interactive = sum(1 for l in lines if any(k in l.lower() for k in ['button', 'input', 'link', 'select', 'textarea']))
    has_landmarks = any(k in snapshot_text.lower() for k in ['navigation', 'main', 'banner', 'contentinfo'])
    has_aria = any(k in snapshot_text.lower() for k in ['aria-', 'role=', 'ref='])

    return {
        'total_elements': total_elements,
        'interactive_elements': interactive,
        'has_landmarks': has_landmarks,
        'has_aria': has_aria,
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


def collect_bounding_box(ref: str) -> Optional[Dict]:
    """agent-browser get box로 요소의 바운딩 박스를 가져옵니다.

    Returns: {'x': float, 'y': float, 'width': float, 'height': float} or None
    """
    try:
        output = _run_ab(['get', 'box', ref], json_output=True)
        data = json.loads(output)
        if data.get('success'):
            return data['data']
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def collect_styles(ref: str, *properties: str) -> Optional[Dict]:
    """agent-browser get styles로 요소의 계산된 CSS 값을 가져옵니다.

    Returns: {'font-size': '14px', 'color': 'rgb(17, 24, 39)', ...} or None
    """
    try:
        args = ['get', 'styles', ref] + list(properties)
        output = _run_ab(args, json_output=True)
        data = json.loads(output)
        if data.get('success') and 'styles' in data.get('data', {}):
            return data['data']['styles']
    except (json.JSONDecodeError, subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def collect_visual_from_boxes(expected_refs: list[str]) -> Dict:
    """주요 요소의 바운딩 박스를 검증하여 레이아웃 점수를 산출합니다.

    - 요소 존재 여부 (box != None)
    - 합리적인 크기 (width > 0, height > 0)
    - 뷰포트 내 위치 (x >= 0, y >= 0)
    """
    total = len(expected_refs)
    if total == 0:
        return {'visual_score': 50, 'checks': []}

    passed = 0
    checks = []
    for ref in expected_refs:
        box = collect_bounding_box(ref)
        ok = (box is not None
              and box.get('width', 0) > 0
              and box.get('height', 0) > 0
              and box.get('x', -1) >= 0
              and box.get('y', -1) >= 0)
        passed += int(ok)
        checks.append({'ref': ref, 'box': box, 'ok': ok})

    return {
        'visual_score': round(passed / total * 100),
        'passed': passed,
        'total': total,
        'checks': checks
    }


def take_annotated_screenshot(output_path: str) -> bool:
    """주석 스크린샷을 캡처합니다."""
    try:
        _run_ab(['screenshot', '--annotate', output_path])
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


if __name__ == '__main__':
    # 테스트용 더미 실행
    print(json.dumps({
        'error': collect_from_console(''),
        'dom': collect_from_snapshot('button\ninput\nlink\nmain\naria-label'),
        'form': collect_form_result(True),
        'visual': collect_visual_from_boxes([])
    }, indent=2))
