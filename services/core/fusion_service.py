"""퓨전 오케스트레이터 — 3단계 파이프라인으로 다중 소스 융합 콘텐츠 생성"""
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from services.core import ai_service, content_service
from services.data import web_research_service
from prompts import build_full_prompt
from prompts.fusion.fusion_prompt import FUSION_PROMPT, build_fusion_context

logger = logging.getLogger(__name__)

MAX_URLS = 5
MIN_URLS = 2
MAX_COMMENTS_PER_VIDEO = 50


def _phase1_collect(urls: List[str]) -> tuple:
    """Phase 1: URL 목록에서 자막과 댓글을 병렬 수집합니다.

    Returns:
        (transcripts, all_comments, total_comments, failed_urls)
    """
    transcripts = []
    all_comments = []
    failed_urls = []
    total_comments = 0

    with ThreadPoolExecutor(max_workers=5) as executor:
        transcript_futures = {}
        comment_futures = {}

        for url in urls:
            vid = content_service.get_video_id(url)
            if not vid:
                failed_urls.append(url)
                continue
            transcript_futures[executor.submit(
                content_service.get_transcript, vid
            )] = (vid, url)
            comment_futures[executor.submit(
                content_service.get_top_comments, vid, MAX_COMMENTS_PER_VIDEO
            )] = vid

        for future in as_completed(transcript_futures):
            vid, url = transcript_futures[future]
            try:
                result = future.result()
                if result and result.get('text'):
                    transcripts.append({'video_id': vid, 'url': url, 'text': result['text']})
                else:
                    failed_urls.append(url)
            except Exception as e:
                logger.warning('자막 추출 실패 (%s): %s', url, e)
                failed_urls.append(url)

        for future in as_completed(comment_futures):
            try:
                comments = future.result()
                if comments:
                    all_comments.extend(comments)
                    total_comments += len(comments)
            except Exception:
                pass

    return transcripts, all_comments, total_comments, failed_urls


def _phase2_analyze(
    transcripts: list, all_comments: list, model: str,
    enable_web_research: bool, enable_deep_comments: bool,
) -> tuple:
    """Phase 2: 자막 요약, 댓글 분석, 웹 리서치를 병렬 수행합니다.

    Returns:
        (video_summaries, comment_analysis, web_sources, tokens_used, task_failures)
    """
    video_summaries = []
    comment_analysis = None
    web_sources = []
    tokens_used = 0
    task_failures = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        for t in transcripts:
            fut = executor.submit(_summarize_transcript, t['text'], t['video_id'], model)
            futures[fut] = ('summary', t)

        if enable_deep_comments and all_comments:
            fut = executor.submit(_analyze_comments, all_comments, model)
            futures[fut] = ('comments', None)

        if enable_web_research:
            transcript_texts = [t['text'] for t in transcripts]
            fut = executor.submit(web_research_service.research_topic, transcript_texts, model)
            futures[fut] = ('web', None)

        for future in as_completed(futures):
            task_type, meta = futures[future]
            try:
                result = future.result()
                if task_type == 'summary' and result:
                    video_summaries.append({
                        'title': result.get('title', meta['video_id']),
                        'summary': result.get('content', ''),
                        'url': meta['url'],
                    })
                    tokens_used += result.get('usage', {}).get('total_tokens', 0)
                elif task_type == 'comments' and result:
                    comment_analysis = result
                    tokens_used += result.get('usage', {}).get('total_tokens', 0)
                elif task_type == 'web' and result:
                    web_sources = result
            except Exception as e:
                logger.warning('Phase 2 작업 실패 (%s): %s', task_type, e)
                failure = {'task': task_type}
                if task_type == 'summary' and meta:
                    failure['video_id'] = meta.get('video_id', '')
                task_failures.append(failure)

    return video_summaries, comment_analysis, web_sources, tokens_used, task_failures


def _add_warning(warnings: List[str], message: str) -> None:
    """중복 없이 사용자 표시용 경고를 누적합니다."""
    if message and message not in warnings:
        warnings.append(message)


def _has_phase2_failure(task_failures: List[Dict[str, Any]], task_name: str) -> bool:
    return any(failure.get('task') == task_name for failure in task_failures)


def _comment_analysis_has_content(comment_analysis: Any) -> bool:
    if not isinstance(comment_analysis, dict):
        return False
    if str(comment_analysis.get('content') or '').strip():
        return True
    return any(comment_analysis.get(key) for key in ('insights', 'questions', 'fact_checks', 'sentiments'))


def _build_diagnostics(
    urls: List[str],
    model: str,
    transcripts: List[Dict[str, Any]],
    video_summaries: List[Dict[str, Any]],
    failed_urls: List[str],
    total_comments: int,
    comment_analysis: Any,
    web_sources: List[Dict[str, Any]],
    phase2_failures: List[Dict[str, Any]],
    enable_web_research: bool,
    enable_deep_comments: bool,
    final_result: Dict[str, Any],
) -> tuple:
    """퓨전 결과의 실행 추적과 저비용 품질 요약을 생성합니다."""
    warnings: List[str] = []
    requested_count = len(urls)
    transcript_count = len(transcripts)
    summary_count = len(video_summaries)
    failed_count = len(failed_urls)
    web_source_count = len(web_sources)
    comment_reflected = _comment_analysis_has_content(comment_analysis)
    comments_analyzed = min(total_comments, 100) if comment_reflected else 0
    final_has_content = bool(final_result.get('content') or final_result.get('html'))

    source_status = 'ok'
    if transcript_count == 0:
        source_status = 'error'
        _add_warning(warnings, '자막을 수집한 영상이 없습니다.')
    elif failed_count > 0:
        source_status = 'warning'
        _add_warning(warnings, f'{failed_count}개 URL의 자막 수집에 실패했습니다.')
    if summary_count < transcript_count:
        source_status = 'warning' if source_status != 'error' else source_status
        _add_warning(warnings, f'{transcript_count - summary_count}개 영상 요약 단계가 비어 있습니다.')

    if not enable_deep_comments:
        comment_status = 'disabled'
    elif total_comments == 0:
        comment_status = 'warning'
        _add_warning(warnings, '댓글 분석이 켜져 있지만 수집된 댓글이 없습니다.')
    elif _has_phase2_failure(phase2_failures, 'comments') or not comment_reflected:
        comment_status = 'warning'
        _add_warning(warnings, '댓글 분석 결과가 비어 있어 최종 반영이 제한되었습니다.')
    else:
        comment_status = 'ok'

    if not enable_web_research:
        web_status = 'disabled'
    elif _has_phase2_failure(phase2_failures, 'web') or web_source_count == 0:
        web_status = 'warning'
        _add_warning(warnings, '웹 리서치가 켜져 있지만 발견된 외부 소스가 없습니다.')
    else:
        web_status = 'ok'

    final_status = 'ok' if final_has_content else 'warning'
    if not final_has_content:
        _add_warning(warnings, '최종 생성 결과 본문이 비어 있습니다.')

    overall_status = 'error' if source_status == 'error' else ('warning' if warnings else 'ok')

    pipeline_trace = {
        'pipeline': 'fusion',
        'model': model,
        'steps': [
            {
                'name': 'transcript_collect',
                'status': 'error' if transcript_count == 0 else ('warning' if failed_count else 'success'),
                'requested_count': requested_count,
                'count': transcript_count,
                'failed_count': failed_count,
                'failed_urls': failed_urls,
            },
            {
                'name': 'transcript_summarize',
                'status': 'success' if summary_count == transcript_count else ('warning' if summary_count else 'error'),
                'requested_count': transcript_count,
                'count': summary_count,
            },
            {
                'name': 'comment_collect',
                'status': 'warning' if enable_deep_comments and total_comments == 0 else 'success',
                'count': total_comments,
            },
            {
                'name': 'comment_analyze',
                'enabled': enable_deep_comments,
                'status': 'success' if comment_status in ('ok', 'disabled') else 'warning',
                'collected_count': total_comments,
                'analyzed_count': comments_analyzed,
            },
            {
                'name': 'web_research',
                'enabled': enable_web_research,
                'status': 'success' if web_status in ('ok', 'disabled') else 'warning',
                'sources_found': web_source_count,
            },
            {
                'name': 'final_generation',
                'status': 'success' if final_has_content else 'warning',
                'has_content': final_has_content,
            },
        ],
        'warnings': warnings,
    }

    quality_summary = {
        'status': overall_status,
        'source_coverage': {
            'status': source_status,
            'requested_count': requested_count,
            'collected_count': transcript_count,
            'summary_count': summary_count,
            'failed_count': failed_count,
        },
        'comment_reflection': {
            'status': comment_status,
            'enabled': enable_deep_comments,
            'collected_count': total_comments,
            'analyzed_count': comments_analyzed,
            'reflected': comment_reflected,
        },
        'web_research': {
            'status': web_status,
            'enabled': enable_web_research,
            'sources_found': web_source_count,
        },
        'final_generation': {
            'status': final_status,
            'has_content': final_has_content,
        },
        'warnings': warnings,
    }
    return pipeline_trace, quality_summary


def generate_fusion(urls: List[str], style_id: str, model: str, modifiers: Dict[str, Any],
                    enable_web_research: bool = True, enable_deep_comments: bool = True) -> Dict[str, Any]:
    """퓨전 파이프라인 실행: Phase 1(수집) → Phase 2(분석) → Phase 3(생성)

    Args:
        urls: YouTube URL 리스트 (2~5개)
        style_id: 스타일 ID
        model: LiteLLM 모델 ID
        modifiers: {'length': str, 'writing_style': str}
        enable_web_research: 웹 리서치 활성화
        enable_deep_comments: 댓글 심층 분석 활성화

    Returns:
        dict: {title, content, html, sections, fusion_meta, pipeline_trace, quality_summary, usage}

    Raises:
        ValueError: URL이 2개 미만이거나 5개 초과 시
    """
    if len(urls) < MIN_URLS:
        raise ValueError(f'퓨전 분석은 최소 {MIN_URLS}개 URL이 필요합니다')
    if len(urls) > MAX_URLS:
        raise ValueError(f'퓨전 분석은 최대 {MAX_URLS}개 URL까지 가능합니다')

    start_time = time.time()

    # Phase 1: 소스 수집
    transcripts, all_comments, total_comments, failed_urls = _phase1_collect(urls)
    if not transcripts:
        raise ValueError('모든 영상의 자막 추출에 실패했습니다')

    # Phase 2: 분석 & 압축
    video_summaries, comment_analysis, web_sources, phase2_tokens, phase2_failures = _phase2_analyze(
        transcripts, all_comments, model, enable_web_research, enable_deep_comments,
    )

    # Phase 3: 융합 & 생성 (모디파이어는 create_content가 [추가 지시사항]으로 1회 주입)
    style_prompt = build_full_prompt(style_id)
    fusion_context = build_fusion_context(video_summaries, comment_analysis, web_sources)
    combined_prompt = f'{FUSION_PROMPT}\n\n{style_prompt}'

    final_result = ai_service.create_content(
        content=fusion_context, model=model,
        style_prompt=combined_prompt, modifiers=modifiers, style_id=style_id,
    )
    total_tokens = phase2_tokens + final_result.get('usage', {}).get('total_tokens', 0)

    # 응답 조합
    sections: Dict[str, Any] = {'faq': '', 'fact_checks': [], 'sources_used': []}
    if comment_analysis and comment_analysis.get('fact_checks'):
        sections['fact_checks'] = comment_analysis['fact_checks']
    for t in transcripts:
        sections['sources_used'].append({'type': 'youtube', 'title': t['video_id'], 'url': t['url']})
    for ws in web_sources:
        sections['sources_used'].append({'type': 'web', 'title': ws['title'], 'url': ws['url']})

    pipeline_trace, quality_summary = _build_diagnostics(
        urls=urls,
        model=model,
        transcripts=transcripts,
        video_summaries=video_summaries,
        failed_urls=failed_urls,
        total_comments=total_comments,
        comment_analysis=comment_analysis,
        web_sources=web_sources,
        phase2_failures=phase2_failures,
        enable_web_research=enable_web_research,
        enable_deep_comments=enable_deep_comments,
        final_result=final_result,
    )

    return {
        'title': final_result.get('title', ''),
        'content': final_result.get('content', ''),
        'html': final_result.get('html', ''),
        'sections': sections,
        'fusion_meta': {
            'videos_analyzed': len(transcripts),
            'comments_analyzed': total_comments,
            'web_sources_found': len(web_sources),
            'total_tokens': total_tokens,
            'processing_time': round(time.time() - start_time, 1),
            'failed_urls': failed_urls,
        },
        'pipeline_trace': pipeline_trace,
        'quality_summary': quality_summary,
        'usage': final_result.get('usage', {}),
    }


def _coerce_list(value: Any) -> List[str]:
    """댓글 분석 JSON 필드를 문자열 리스트로 정규화합니다."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _parse_comment_analysis(content: str) -> Dict[str, Any]:
    """댓글 분석 LLM 출력을 구조화합니다. JSON 실패 시 원문 fallback을 보존합니다."""
    raw = (content or '').strip()
    if not raw:
        return {'content': '', 'insights': [], 'questions': [], 'fact_checks': [], 'sentiments': []}

    candidate = raw
    fence_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw, re.IGNORECASE)
    if fence_match:
        candidate = fence_match.group(1).strip()

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return {
                'content': raw,
                'insights': _coerce_list(parsed.get('insights') or parsed.get('인사이트')),
                'questions': _coerce_list(parsed.get('questions') or parsed.get('질문')),
                'fact_checks': _coerce_list(parsed.get('fact_checks') or parsed.get('factChecks') or parsed.get('팩트체크')),
                'sentiments': _coerce_list(parsed.get('sentiments') or parsed.get('감상') or parsed.get('sentiment')),
            }
    except Exception:
        pass

    # 구조화 실패해도 최종 퓨전 프롬프트에서 댓글 분석 원문을 사용하도록 보존
    return {'content': raw, 'insights': [], 'questions': [], 'fact_checks': [], 'sentiments': []}


def _analyze_comments(comments: list, model: str) -> dict:
    """댓글 목록을 AI로 분석하여 핵심 인사이트를 추출합니다."""
    comments_text = "\n".join(comments[:100])
    prompt = (
        "다음 YouTube 댓글을 분석하여 주요 의견, FAQ로 쓸 질문, 팩트체크 필요 항목, "
        "시청자 감정을 JSON 형식으로 정리하세요.\n"
        "반드시 다음 키를 가진 JSON 객체만 출력하세요: "
        "insights, questions, fact_checks, sentiments. 각 값은 문자열 배열입니다.\n\n"
        f"{comments_text[:5000]}"
    )
    result = ai_service.create_content(
        content=prompt, model=model,
        style_prompt="댓글 분석 요약. JSON만 출력.",
        style_id="summary"
    )
    if isinstance(result, tuple):
        result = result[0]
    parsed = _parse_comment_analysis(result.get('content', ''))
    parsed['usage'] = result.get('usage', {})
    return parsed


def _summarize_transcript(text, video_id, model):
    """개별 영상 자막을 구조화된 요약으로 변환"""
    prompt = (
        '다음 YouTube 영상 자막을 500자 이내로 구조화하여 요약하세요.\n'
        '핵심 주장, 근거, 결론을 구분하여 정리하세요.\n'
        '제목도 한 줄로 작성하세요.\n\n'
        f'{text[:8000]}'
    )
    return ai_service.create_content(
        content=prompt, model=model,
        style_prompt='구조화된 요약. 제목 + 핵심 주장 + 근거 + 결론.',
        style_id='summary'
    )
