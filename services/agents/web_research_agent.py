"""
자동 리서치 에이전트 — 주제 검색 → 기사 수집 → AI 요약 → 품질 평가
BaseAgent의 plan/execute/reflect 패턴을 따릅니다.
"""
import logging
from typing import Any, Dict

from services.agents.base_framework import BaseAgent
from services.core import ai_service
from services.data.web_research_service import search_web, crawl_article

logger = logging.getLogger(__name__)

# 기본 설정
DEFAULT_MAX_SOURCES = 5
DEFAULT_MAX_ITERATIONS = 3


class ResearchAgent(BaseAgent):
    """주제 기반 웹 리서치 에이전트.

    plan: 주제 → 검색 쿼리 생성
    execute: 웹 검색 → 기사 크롤링 → AI 요약
    reflect: 결과 품질 평가 → 부족하면 추가 검색
    """

    def __init__(self, model: str, max_sources: int = DEFAULT_MAX_SOURCES,
                 max_iterations: int = DEFAULT_MAX_ITERATIONS):
        super().__init__(name="ResearchAgent", model=model, max_iterations=max_iterations)
        self.max_sources = max_sources

    def plan(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """주제에서 검색 쿼리를 생성합니다."""
        feedback = context.get("feedback", "")

        # 피드백이 있으면 쿼리 보완 프롬프트 추가
        if feedback:
            prompt = (
                f"이전 검색 결과가 부족했습니다. 피드백: {feedback}\n\n"
                f"주제: {task}\n\n"
                "다른 각도에서 3~5개의 검색 쿼리를 쉼표로 구분하여 출력하세요. "
                "쿼리만 출력하세요."
            )
        else:
            prompt = (
                f"다음 주제에 대해 웹 검색할 쿼리를 3~5개 생성하세요.\n\n"
                f"주제: {task}\n\n"
                "쉼표로 구분하여 쿼리만 출력하세요."
            )

        try:
            result = ai_service.create_content(
                content=prompt, model=self.model,
                style_prompt="검색 쿼리만 쉼표로 구분하여 출력하세요.",
                style_id="summary"
            )
            raw = result.get("content", "")
            queries = [q.strip() for q in raw.split(",") if q.strip()][:5]
        except Exception as e:
            logger.warning(f"검색 쿼리 생성 실패: {e}")
            # 주제 자체를 쿼리로 사용
            queries = [task]

        return {"queries": queries, "summary": f"검색 쿼리 {len(queries)}개 생성"}

    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """검색 → 크롤링 → 요약을 수행합니다."""
        queries = plan.get("queries", [])
        if not queries:
            return {"sources": [], "summary": "검색 쿼리 없음"}

        # 쿼리 합쳐서 검색
        all_results = []
        seen_urls = set()
        for query in queries:
            results = search_web([query], max_results=self.max_sources)
            for r in results:
                url = r.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)

        if not all_results:
            return {"sources": [], "summary": "검색 결과 없음"}

        # 상위 max_sources개만 크롤링
        targets = all_results[:self.max_sources]

        # 크롤링 + 요약
        sources = []
        for item in targets:
            text = crawl_article(item.get("url", ""))
            if not text:
                continue

            try:
                summary_result = ai_service.create_content(
                    content=f"다음 기사를 200자 이내로 핵심만 요약하세요:\n\n{text[:3000]}",
                    model=self.model,
                    style_prompt="200자 이내 핵심 요약만 출력하세요.",
                    style_id="summary"
                )
                sources.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "summary": summary_result.get("content", ""),
                    "text_length": len(text),
                })
            except Exception as e:
                logger.warning(f"기사 요약 실패 ({item.get('url')}): {e}")

        return {
            "sources": sources,
            "source_count": len(sources),
            "summary": f"{len(sources)}개 소스 수집 및 요약 완료",
        }

    def reflect(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """결과 품질을 평가합니다."""
        sources = result.get("sources", [])

        # 소스가 충분하면 완료
        if len(sources) >= 3:
            return {"done": True, "feedback": "", "quality": "good"}

        # 소스가 있지만 부족
        if sources:
            return {
                "done": False,
                "feedback": f"소스가 {len(sources)}개로 부족합니다. 다른 키워드로 추가 검색이 필요합니다.",
                "quality": "partial",
            }

        # 소스 없음
        return {
            "done": False,
            "feedback": "검색 결과가 없습니다. 더 일반적인 키워드로 재시도해주세요.",
            "quality": "poor",
        }
