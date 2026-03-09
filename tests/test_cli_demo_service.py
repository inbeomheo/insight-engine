"""CLI 데모 서비스 테스트"""

import unittest
from services.cli_demo_service import (
    CLICommand, CLIDemo,
    create_demo, generate_script, validate_commands,
)


class TestCLIDemoService(unittest.TestCase):
    """CLI 데모 서비스 테스트"""

    def _make_commands(self):
        return [
            {
                "command": "insight-engine generate",
                "description": "콘텐츠 생성",
                "args": ["--url", "https://youtube.com/watch?v=123"],
                "output": "콘텐츠가 생성되었습니다.",
            },
            {
                "command": "insight-engine styles",
                "description": "스타일 목록",
                "args": [],
                "output": "14개 스타일이 있습니다.",
            },
        ]

    def test_create_demo(self):
        """데모 생성"""
        demo = create_demo("퀵스타트", self._make_commands())
        self.assertEqual(demo.title, "퀵스타트")
        self.assertEqual(len(demo.commands), 2)

    def test_create_demo_empty_commands(self):
        """빈 명령어 목록"""
        demo = create_demo("빈 데모", [])
        self.assertEqual(len(demo.commands), 0)

    def test_create_demo_has_setup(self):
        """설정 지침 포함"""
        demo = create_demo("데모", [])
        self.assertTrue(len(demo.setup_instructions) > 0)

    def test_generate_script_bash(self):
        """Bash 스크립트 생성"""
        demo = create_demo("데모", self._make_commands())
        script = generate_script(demo, "bash")
        self.assertIn("#!/bin/bash", script)
        self.assertIn("insight-engine generate", script)
        self.assertIn("--url", script)

    def test_generate_script_powershell(self):
        """PowerShell 스크립트 생성"""
        demo = create_demo("데모", self._make_commands())
        script = generate_script(demo, "powershell")
        self.assertIn("insight-engine generate", script)
        self.assertNotIn("#!/bin/bash", script)

    def test_generate_script_invalid_shell(self):
        """지원하지 않는 셸"""
        demo = create_demo("데모", self._make_commands())
        with self.assertRaises(ValueError):
            generate_script(demo, "fish")

    def test_generate_script_includes_description(self):
        """설명 포함"""
        demo = create_demo("데모", self._make_commands())
        script = generate_script(demo, "bash")
        self.assertIn("콘텐츠 생성", script)

    def test_generate_script_includes_output(self):
        """예상 출력 포함"""
        demo = create_demo("데모", self._make_commands())
        script = generate_script(demo, "bash")
        self.assertIn("예상 출력", script)

    def test_validate_commands_valid(self):
        """유효한 명령어"""
        demo = create_demo("데모", self._make_commands())
        issues = validate_commands(demo)
        self.assertEqual(issues, [])

    def test_validate_commands_empty_command(self):
        """빈 명령어"""
        demo = create_demo("데모", [{"command": "", "description": "설명", "args": [], "output": "결과"}])
        issues = validate_commands(demo)
        self.assertTrue(any("명령어가 비어" in i for i in issues))

    def test_validate_commands_empty_description(self):
        """빈 설명"""
        demo = create_demo("데모", [{"command": "cmd", "description": "", "args": [], "output": "결과"}])
        issues = validate_commands(demo)
        self.assertTrue(any("설명이 비어" in i for i in issues))

    def test_validate_commands_empty_output(self):
        """빈 예상 출력"""
        demo = create_demo("데모", [{"command": "cmd", "description": "설명", "args": [], "output": ""}])
        issues = validate_commands(demo)
        self.assertTrue(any("예상 출력이 비어" in i for i in issues))

    def test_validate_commands_no_commands(self):
        """명령어 없음"""
        demo = create_demo("데모", [])
        issues = validate_commands(demo)
        self.assertTrue(any("명령어가 없" in i for i in issues))

    def test_generate_script_title_in_comment(self):
        """스크립트에 제목 포함"""
        demo = create_demo("My Demo Script", self._make_commands())
        script = generate_script(demo, "bash")
        self.assertIn("My Demo Script", script)


if __name__ == "__main__":
    unittest.main()
