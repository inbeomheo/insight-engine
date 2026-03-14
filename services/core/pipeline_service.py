"""AI 콘텐츠 생성 파이프라인 서비스

스텝별 순차 실행 + SSE 진행률 이벤트를 yield하는 파이프라인 엔진.
기존 서비스 함수(content_service, ai_service)를 래핑하여 사용.
"""
from dataclasses import dataclass, field
from typing import Generator, Callable, Dict, Optional
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class PipelineStep:
    """파이프라인 단일 스텝 정의"""
    id: str
    name: str
    description: str
    handler: Callable[[dict], Optional[dict]]


@dataclass
class PipelineConfig:
    """파이프라인 설정 (스텝 목록)"""
    id: str
    name: str
    steps: list[PipelineStep] = field(default_factory=list)


class PipelineEngine:
    """파이프라인 실행 엔진. 각 스텝마다 진행률 이벤트를 yield."""

    def __init__(self, config: PipelineConfig):
        self.config = config

    def execute(self, context: dict) -> Generator[dict, None, None]:
        """파이프라인을 실행하고 각 스텝마다 SSE 이벤트를 yield합니다.

        Args:
            context: 스텝 간 공유되는 데이터 딕셔너리.
                     각 스텝의 handler가 반환한 dict로 업데이트됩니다.

        Yields:
            dict: SSE 이벤트
                - step_start: 스텝 시작 (step, name, description, progress)
                - step_complete: 스텝 완료 (step, progress, elapsed)
                - step_error: 스텝 에러 (step, error)
                - pipeline_complete: 전체 완료 (progress, result)
        """
        total = len(self.config.steps)
        if total == 0:
            yield {"type": "pipeline_complete", "progress": 1.0, "result": context}
            return

        for i, step in enumerate(self.config.steps):
            progress = i / total
            yield {
                "type": "step_start",
                "step": step.id,
                "name": step.name,
                "description": step.description,
                "progress": progress,
            }

            step_start = time.time()
            try:
                result = step.handler(context)
                if result:
                    context.update(result)
                elapsed = round(time.time() - step_start, 2)
                yield {
                    "type": "step_complete",
                    "step": step.id,
                    "progress": (i + 1) / total,
                    "elapsed": elapsed,
                }
            except Exception as e:
                logger.error("파이프라인 스텝 '%s' 에러: %s", step.id, e)
                yield {
                    "type": "step_error",
                    "step": step.id,
                    "error": f"'{step.name}' 처리 중 오류가 발생했습니다.",
                    "progress": (i + 1) / total,
                }
                return

        yield {"type": "pipeline_complete", "progress": 1.0, "result": context}


# ==================== 기본 스텝 핸들러 ====================
# 기존 서비스 함수를 래핑하여 파이프라인 context와 연동

def _step_extract_transcript(ctx: dict) -> dict:
    """YouTube 자막을 추출합니다. (content_service 래핑)"""
    from services.core import content_service
    from config import get_model_max_tokens

    url = ctx.get("url", "")
    video_id = content_service.get_video_id(url)
    if not video_id:
        raise ValueError("유효하지 않은 YouTube URL입니다.")

    # 자막 추출
    transcript_result = content_service.get_transcript(video_id)
    if isinstance(transcript_result, dict) and transcript_result.get("error"):
        raise ValueError(transcript_result["error"])

    transcript_text = transcript_result.get("text", "")
    transcript_source = transcript_result.get("source", "unknown")

    # 댓글 수집
    comments = content_service.get_top_comments(video_id) or []

    # YouTube 제목
    youtube_title = content_service.get_content_title(url) or "YouTube 영상"

    # 콘텐츠 조합
    main_content = f"[영상 자막]\n{transcript_text}"
    if comments:
        comments_text = "\n".join(comments[:20])
        main_content = f"[영상 자막]\n{transcript_text}\n\n[시청자 댓글]\n{comments_text}"

    # 토큰 제한
    model = ctx.get("model", "")
    max_tokens = get_model_max_tokens(model)
    truncated = content_service.truncate_text(main_content, max_tokens)

    return {
        "video_id": video_id,
        "transcript_text": transcript_text,
        "transcript_source": transcript_source,
        "youtube_title": youtube_title,
        "comments": comments,
        "truncated_content": truncated,
    }


def _step_generate_content(ctx: dict) -> dict:
    """AI 콘텐츠를 생성합니다. (ai_service 래핑)"""
    from services.core import ai_service
    from prompts import STYLE_PROMPTS, build_full_prompt

    content = ctx.get("truncated_content", "")
    model = ctx.get("model", "")
    style = ctx.get("style", "blog_seo")
    modifiers = ctx.get("modifiers")
    custom_prompt = ctx.get("custom_prompt")

    # 스타일 프롬프트 결정
    if custom_prompt and custom_prompt.strip():
        style_prompt = custom_prompt.strip()[:2000]
    else:
        style_prompt = STYLE_PROMPTS.get(style, "")

    result, prompt = ai_service.create_content(
        content, model,
        style_prompt=style_prompt,
        return_prompt=True,
        modifiers=modifiers,
        style_id=style,
    )

    return {
        "title": result.get("title", ""),
        "content": result.get("content", ""),
        "html": result.get("html", ""),
        "usage": result.get("usage", {}),
        "prompt": prompt,
    }


def _step_extract_seo(ctx: dict) -> dict:
    """SEO 메타데이터를 추출합니다. (ai_service.extract_seo_metadata 래핑)"""
    from services.core import ai_service

    style = ctx.get("style", "")
    body = ctx.get("content", "")

    seo = None
    geo = None

    if style == "blog_seo" and body:
        seo = ai_service.extract_seo_metadata(body)

    if style == "geo_seo" and body:
        geo = ai_service.extract_geo_metadata(body)

    result = {}
    if seo:
        result["seo"] = seo
    if geo:
        result["geo"] = geo
    return result


# ==================== 프리셋 ====================

BLOG_AUTOMATION = PipelineConfig(
    id="blog_automation",
    name="블로그 자동화",
    steps=[
        PipelineStep(
            "transcript", "자막 추출",
            "YouTube 자막과 댓글을 가져옵니다",
            _step_extract_transcript,
        ),
        PipelineStep(
            "generate", "콘텐츠 생성",
            "AI가 블로그 글을 작성합니다",
            _step_generate_content,
        ),
        PipelineStep(
            "seo", "SEO 최적화",
            "SEO/GEO 메타데이터를 추출합니다",
            _step_extract_seo,
        ),
    ],
)

PIPELINE_PRESETS: Dict[str, PipelineConfig] = {
    "blog_automation": BLOG_AUTOMATION,
}
