"""브라우저 에이전트 서비스 테스트"""
import unittest
from services.browser_agent_service import (
    create_script, validate_script, simulate_execution, export_script,
    BrowserScript, BrowserAction
)


class TestBrowserAgentService(unittest.TestCase):

    def setUp(self):
        self.actions_config = [
            {'action_type': 'navigate', 'target': 'https://example.com'},
            {'action_type': 'click', 'target': '#login-btn'},
            {'action_type': 'type', 'target': '#username', 'value': 'admin'},
            {'action_type': 'screenshot', 'target': 'result.png'},
        ]
        self.script = create_script('로그인 테스트', self.actions_config)

    def test_create_script(self):
        self.assertIsInstance(self.script, BrowserScript)
        self.assertEqual(self.script.name, '로그인 테스트')
        self.assertEqual(len(self.script.actions), 4)

    def test_validate_script_valid(self):
        errors = validate_script(self.script)
        self.assertEqual(len(errors), 0)

    def test_validate_script_no_actions(self):
        script = create_script('빈', [])
        errors = validate_script(script)
        self.assertIn('액션이 없습니다.', errors)

    def test_validate_script_first_not_navigate(self):
        script = create_script('잘못된', [
            {'action_type': 'click', 'target': '#btn'}
        ])
        errors = validate_script(script)
        self.assertTrue(any('navigate' in e for e in errors))

    def test_validate_script_empty_target(self):
        script = create_script('테스트', [
            {'action_type': 'navigate', 'target': 'https://x.com'},
            {'action_type': 'click', 'target': ''},
        ])
        errors = validate_script(script)
        self.assertTrue(any('target' in e for e in errors))

    def test_simulate_execution(self):
        result = simulate_execution(self.script)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['step_count'], 4)
        self.assertGreater(result['total_time_ms'], 0)

    def test_simulate_execution_all_success(self):
        result = simulate_execution(self.script)
        for step in result['steps']:
            self.assertEqual(step['status'], 'success')

    def test_export_script_playwright(self):
        output = export_script(self.script, 'playwright')
        self.assertIn('chromium', output)
        self.assertIn('page.goto', output)
        self.assertIn('page.click', output)

    def test_export_script_selenium(self):
        output = export_script(self.script, 'selenium')
        self.assertIn('webdriver', output)
        self.assertIn('driver.get', output)

    def test_script_default_timeout(self):
        self.assertEqual(self.script.actions[0].timeout_ms, 5000)

    def test_validate_script_negative_timeout(self):
        script = create_script('t', [
            {'action_type': 'navigate', 'target': 'http://x', 'timeout_ms': -1}
        ])
        errors = validate_script(script)
        self.assertTrue(any('timeout' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
