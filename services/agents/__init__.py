"""
멀티에이전트 파이프라인 패키지

두 가지 에이전트 시스템을 통합:
- 콘텐츠 파이프라인: Research → Writer → Editor → SEO (execute 패턴)
- 범용 프레임워크: plan → execute → reflect 루프 (base_framework)
"""
from .base_agent import BaseAgent
from .research_agent import ResearchAgent
from .writer_agent import WriterAgent
from .editor_agent import EditorAgent
from .seo_agent import SEOAgent
from .orchestrator import Orchestrator
from .base_framework import (
    BaseAgent as FrameworkBaseAgent,
    AgentEvent,
    EVENT_PLAN,
    EVENT_EXECUTE,
    EVENT_REFLECT,
    EVENT_DONE,
    EVENT_ERROR,
)
from .pipeline_orchestrator import AgentOrchestrator

__all__ = [
    'BaseAgent',
    'ResearchAgent',
    'WriterAgent',
    'EditorAgent',
    'SEOAgent',
    'Orchestrator',
    'FrameworkBaseAgent',
    'AgentEvent',
    'AgentOrchestrator',
]
