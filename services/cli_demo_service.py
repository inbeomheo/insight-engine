"""
CLI 데모 서비스 — CLI 명령어 데모 스크립트 생성
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class CLICommand:
    """CLI 명령어"""
    command: str
    description: str
    example_args: list  # ["--url", "https://..."]
    expected_output: str


@dataclass
class CLIDemo:
    """CLI 데모"""
    demo_id: str
    title: str
    commands: list  # list[CLICommand]
    setup_instructions: str


def create_demo(title: str, commands_config: list) -> CLIDemo:
    """CLI 데모 생성

    commands_config: [{"command": str, "description": str, "args": list, "output": str}]
    """
    commands = []
    for cfg in commands_config:
        commands.append(CLICommand(
            command=cfg.get("command", ""),
            description=cfg.get("description", ""),
            example_args=cfg.get("args", []),
            expected_output=cfg.get("output", ""),
        ))

    return CLIDemo(
        demo_id=str(uuid.uuid4()),
        title=title,
        commands=commands,
        setup_instructions="# 사전 준비\npip install insight-engine-cli",
    )


def generate_script(demo: CLIDemo, shell: str = "bash") -> str:
    """셸 스크립트 생성"""
    lines = []

    if shell == "bash":
        lines.append("#!/bin/bash")
        lines.append(f"# {demo.title}")
        lines.append("")
        lines.append(demo.setup_instructions)
        lines.append("")

        for cmd in demo.commands:
            lines.append(f"# {cmd.description}")
            full_cmd = cmd.command
            if cmd.example_args:
                full_cmd += " " + " ".join(cmd.example_args)
            lines.append(full_cmd)
            if cmd.expected_output:
                lines.append(f"# 예상 출력: {cmd.expected_output}")
            lines.append("")

    elif shell == "powershell":
        lines.append(f"# {demo.title}")
        lines.append("")
        lines.append(demo.setup_instructions.replace("#", "#"))
        lines.append("")

        for cmd in demo.commands:
            lines.append(f"# {cmd.description}")
            full_cmd = cmd.command
            if cmd.example_args:
                full_cmd += " " + " ".join(cmd.example_args)
            lines.append(full_cmd)
            if cmd.expected_output:
                lines.append(f"# 예상 출력: {cmd.expected_output}")
            lines.append("")
    else:
        raise ValueError(f"지원하지 않는 셸: {shell}. 허용: bash, powershell")

    return "\n".join(lines)


def validate_commands(demo: CLIDemo) -> list:
    """명령어 검증 (빈 필드 체크)"""
    issues = []

    if not demo.commands:
        issues.append("명령어가 없습니다")
        return issues

    for i, cmd in enumerate(demo.commands):
        prefix = f"명령어 {i + 1}"
        if not cmd.command.strip():
            issues.append(f"{prefix}: 명령어가 비어있습니다")
        if not cmd.description.strip():
            issues.append(f"{prefix}: 설명이 비어있습니다")
        if not cmd.expected_output.strip():
            issues.append(f"{prefix}: 예상 출력이 비어있습니다")

    return issues
