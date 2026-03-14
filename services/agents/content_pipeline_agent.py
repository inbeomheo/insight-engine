"""
멀티에이전트 콘텐츠 파이프라인 — 리서처 → 작가 → 편집자 → SEO 4단계 체인
각 단계는 BaseAgent를 상속한 단일 목적 에이전트입니다.
"""
import logging
from typing import Any, Dict

from services.agents.base_framework import BaseAgent
from services.core import ai_service

logger = logging.getLogger(__name__)


class WriterAgent(BaseAgent):
    """리서치 결과를 바탕으로 초안을 작성합니다."""

    def __init__(self, model: str, style_id: str = "blog_seo"):
        super().__init__(name="WriterAgent", model=model, max_iterations=2)
        self.style_id = style_id

    def plan(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        sources = context.get("sources", [])
        source_text = "\n".join(
            f"- {s.get('title', '')}: {s.get('summary', '')}" for s in sources
        )
        return {
            "task": task,
            "source_text": source_text,
            "summary": f"소스 {len(sources)}개 기반 초안 작성 계획",
        }

    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            f"다음 주제와 참고 자료를 바탕으로 블로그 글 초안을 작성하세요.\n\n"
            f"주제: {plan['task']}\n\n"
            f"참고 자료:\n{plan.get('source_text', '없음')}\n\n"
            "마크다운 형식으로 작성하세요."
        )
        from prompts import STYLE_PROMPTS
        style_prompt = STYLE_PROMPTS.get(self.style_id, "")
        result = ai_service.create_content(
            content=prompt, model=self.model,
            style_prompt=style_prompt, style_id=self.style_id
        )
        return {"draft": result.get("content", ""), "title": result.get("title", "")}

    def reflect(self, result: Dict[str, Any]) -> Dict[str, Any]:
        draft = result.get("draft", "")
        if len(draft) > 200:
            return {"done": True, "feedback": ""}
        return {"done": False, "feedback": "초안이 너무 짧습니다. 더 상세하게 작성하세요."}


class EditorAgent(BaseAgent):
    """초안을 편집하여 품질을 개선합니다."""

    def __init__(self, model: str):
        super().__init__(name="EditorAgent", model=model, max_iterations=1)

    def plan(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"draft": context.get("draft", ""), "summary": "편집 계획"}

    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        draft = plan.get("draft", "")
        if not draft:
            return {"edited": "", "changes": []}

        prompt = (
            "다음 글을 편집해주세요. 수정 사항:\n"
            "1. 문법/맞춤법 교정\n"
            "2. 문장 흐름 개선\n"
            "3. 불필요한 반복 제거\n"
            "4. 금지 표현(놀라운, 혁신적, 획기적 등) 대체\n\n"
            "편집된 전체 글만 출력하세요.\n\n"
            f"{draft}"
        )
        result = ai_service.create_content(
            content=prompt, model=self.model,
            style_prompt="편집된 글만 출력하세요.", style_id="summary"
        )
        return {"edited": result.get("content", draft)}

    def reflect(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return {"done": True, "feedback": ""}


class SeoAgent(BaseAgent):
    """SEO 메타데이터를 추출/최적화합니다."""

    def __init__(self, model: str):
        super().__init__(name="SeoAgent", model=model, max_iterations=1)

    def plan(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"content": context.get("edited", context.get("draft", "")), "summary": "SEO 분석"}

    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        content = plan.get("content", "")
        if not content:
            return {"seo": {}}

        prompt = (
            "다음 글에서 SEO 메타데이터를 추출하세요.\n\n"
            "JSON 형식으로만 출력하세요:\n"
            '{"meta_description": "...", "keywords": ["..."], "slug": "...", "tags": ["..."]}\n\n'
            f"{content[:3000]}"
        )
        result = ai_service.create_content(
            content=prompt, model=self.model,
            style_prompt="JSON만 출력하세요.", style_id="summary"
        )
        import json
        import re
        raw = result.get("content", "")
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        seo = {}
        if json_match:
            try:
                seo = json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        return {"seo": seo}

    def reflect(self, result: Dict[str, Any]) -> Dict[str, Any]:
        return {"done": True, "feedback": ""}
