"""
브라우저 에이전트 서비스 — 브라우저 자동화 작업 정의/실행 시뮬레이션
"""

import uuid
from dataclasses import dataclass, field


VALID_ACTION_TYPES = ('navigate', 'click', 'type', 'scroll', 'wait', 'screenshot')


@dataclass
class BrowserAction:
    """브라우저 액션"""
    action_id: str
    action_type: str  # navigate / click / type / scroll / wait / screenshot
    target: str
    value: str = ''
    timeout_ms: int = 5000


@dataclass
class BrowserScript:
    """브라우저 스크립트"""
    script_id: str
    name: str
    actions: list[BrowserAction]
    expected_result: str


def create_script(name: str, actions_config: list[dict]) -> BrowserScript:
    """스크립트 생성"""
    actions = []
    for ac in actions_config:
        action = BrowserAction(
            action_id=str(uuid.uuid4())[:8],
            action_type=ac.get('action_type', 'navigate'),
            target=ac.get('target', ''),
            value=ac.get('value', ''),
            timeout_ms=ac.get('timeout_ms', 5000)
        )
        actions.append(action)

    return BrowserScript(
        script_id=str(uuid.uuid4())[:8],
        name=name,
        actions=actions,
        expected_result=''
    )


def validate_script(script: BrowserScript) -> list[str]:
    """스크립트 검증"""
    errors = []

    if not script.actions:
        errors.append('액션이 없습니다.')
        return errors

    # 첫 액션은 navigate여야 함
    if script.actions[0].action_type != 'navigate':
        errors.append('첫 번째 액션은 navigate여야 합니다.')

    for i, action in enumerate(script.actions):
        if action.action_type not in VALID_ACTION_TYPES:
            errors.append(f"액션 {i}: 유효하지 않은 타입 '{action.action_type}'")
        if not action.target and action.action_type != 'screenshot':
            errors.append(f"액션 {i}: target이 비어 있습니다.")
        if action.timeout_ms <= 0:
            errors.append(f"액션 {i}: timeout_ms는 양수여야 합니다.")

    return errors


def simulate_execution(script: BrowserScript) -> dict:
    """실행 시뮬레이션"""
    total_time_ms = 0
    steps = []

    for action in script.actions:
        # 액션별 예상 실행 시간
        time_map = {
            'navigate': 2000,
            'click': 500,
            'type': 1000,
            'scroll': 300,
            'wait': action.timeout_ms,
            'screenshot': 800
        }
        exec_time = time_map.get(action.action_type, 500)
        total_time_ms += exec_time

        steps.append({
            'action_id': action.action_id,
            'action_type': action.action_type,
            'target': action.target,
            'exec_time_ms': exec_time,
            'status': 'success'
        })

    return {
        'script_id': script.script_id,
        'total_time_ms': total_time_ms,
        'step_count': len(steps),
        'steps': steps,
        'status': 'completed'
    }


def export_script(script: BrowserScript, format: str = 'playwright') -> str:
    """Playwright/Selenium 형식 내보내기 시뮬레이션"""
    lines = []

    if format == 'playwright':
        lines.append('const { chromium } = require("playwright");')
        lines.append('')
        lines.append('(async () => {')
        lines.append('  const browser = await chromium.launch();')
        lines.append('  const page = await browser.newPage();')

        for action in script.actions:
            if action.action_type == 'navigate':
                lines.append(f'  await page.goto("{action.target}");')
            elif action.action_type == 'click':
                lines.append(f'  await page.click("{action.target}");')
            elif action.action_type == 'type':
                lines.append(f'  await page.fill("{action.target}", "{action.value}");')
            elif action.action_type == 'scroll':
                lines.append(f'  await page.evaluate(() => window.scrollBy(0, 500));')
            elif action.action_type == 'wait':
                lines.append(f'  await page.waitForTimeout({action.timeout_ms});')
            elif action.action_type == 'screenshot':
                lines.append(f'  await page.screenshot({{ path: "{action.target or "screenshot.png"}" }});')

        lines.append('  await browser.close();')
        lines.append('})();')

    elif format == 'selenium':
        lines.append('from selenium import webdriver')
        lines.append('from selenium.webdriver.common.by import By')
        lines.append('')
        lines.append('driver = webdriver.Chrome()')

        for action in script.actions:
            if action.action_type == 'navigate':
                lines.append(f'driver.get("{action.target}")')
            elif action.action_type == 'click':
                lines.append(f'driver.find_element(By.CSS_SELECTOR, "{action.target}").click()')
            elif action.action_type == 'type':
                lines.append(f'driver.find_element(By.CSS_SELECTOR, "{action.target}").send_keys("{action.value}")')
            elif action.action_type == 'wait':
                lines.append(f'import time; time.sleep({action.timeout_ms / 1000})')

        lines.append('driver.quit()')

    return '\n'.join(lines)
