"""
에이전트 역할별 시스템 프롬프트

AIAgent 생성 시 역할에 맞는 프롬프트를 로드합니다.
"""
from agent.prompts.roles import ROLE_PROMPTS, get_role_prompt

__all__ = ["ROLE_PROMPTS", "get_role_prompt"]
