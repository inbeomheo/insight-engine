"""퓨전 오케스트레이터 — 3단계 파이프라인으로 다중 소스 융합 콘텐츠 생성"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from services import ai_service, content_service
from services import comment_analyzer_service, web_research_service
from prompts import build_full_prompt
from prompts.fusion.fusion_prompt import FUSION_PROMPT, build_fusion_context

logger = logging.getLogger(__name__)

MAX_URLS = 5
MIN_URLS = 2
MAX_COMMENTS_PER_VIDEO = 50


def generate_fusion(urls, style_id, model, modifiers,
                    enable_web_research=True, enable_deep_comments=True):
    """퓨전 파이프라인 실행: Phase 1(수집) → Phase 2(분석) → Phase 3(생성)

    Args:
        urls: YouTube URL 리스트 (2~5개)
        style_id: 스타일 ID
        model: LiteLLM 모델 ID
        modifiers: {'length': str, 'writing_style': str}
        enable_web_research: 웹 리서치 활성화
        enable_deep_comments: 댓글 심층 분석 활성화

    Returns:
        dict: {title, content, html, sections, fusion_meta, usage}

    Raises:
        ValueError: URL이 2개 미만이거나 5개 초과 시
    """
    if len(urls) < MIN_URLS:
        raise ValueError(f'퓨전 분석은 최소 {MIN_URLS}개 URL이 필요합니다')
    if len(urls) > MAX_URLS:
        raise ValueError(f'퓨전 분석은 최대 {MAX_URLS}개 URL까지 가능합니다')

    start_time = time.time()
    total_tokens = 0
    total_comments = 0

    # ── Phase 1: 소스 수집 (병렬) ──
    transcripts = []
    all_comments = []
    failed_urls = []

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

    if not transcripts:
        raise ValueError('모든 영상의 자막 추출에 실패했습니다')

    # ── Phase 2: 분석 & 압축 (병렬) ──
    video_summaries = []
    comment_analysis = None
    web_sources = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}

        # 2a. 영상별 요약
        for t in transcripts:
            fut = executor.submit(
                _summarize_transcript, t['text'], t['video_id'], model
            )
            futures[fut] = ('summary', t)

        # 2b. 댓글 심층 분석
        if enable_deep_comments and all_comments:
            fut = executor.submit(
                comment_analyzer_service.analyze_comments, all_comments, model
            )
            futures[fut] = ('comments', None)

        # 2c. 웹 리서치
        if enable_web_research:
            transcript_texts = [t['text'] for t in transcripts]
            fut = executor.submit(
                web_research_service.research_topic, transcript_texts, model
            )
            futures[fut] = ('web', None)

        for future in as_completed(futures):
            task_type, meta = futures[future]
            try:
                result = future.result()
                if task_type == 'summary' and result:
                    video_summaries.append({
                        'title': result.get('title', meta['video_id']),
                        'summary': result.get('content', ''),
                        'url': meta['url']
                    })
                    total_tokens += result.get('usage', {}).get('total_tokens', 0)
                elif task_type == 'comments' and result:
                    comment_analysis = result
                    total_tokens += result.get('usage', {}).get('total_tokens', 0)
                elif task_type == 'web' and result:
                    web_sources = result
            except Exception as e:
                logger.warning('Phase 2 작업 실패 (%s): %s', task_type, e)

    # ── Phase 3: 융합 & 생성 ──
    style_prompt = build_full_prompt(style_id, modifiers)
    fusion_context = build_fusion_context(video_summaries, comment_analysis, web_sources)
    combined_prompt = f'{FUSION_PROMPT}\n\n{style_prompt}'

    final_result = ai_service.create_content(
        content=fusion_context,
        model=model,
        style_prompt=combined_prompt,
        modifiers=modifiers,
        style_id=style_id
    )
    total_tokens += final_result.get('usage', {}).get('total_tokens', 0)

    # 응답 조합
    sections = {
        'faq': '',
        'fact_checks': [],
        'sources_used': []
    }

    if comment_analysis:
        if comment_analysis.get('fact_checks'):
            sections['fact_checks'] = comment_analysis['fact_checks']

    for t in transcripts:
        sections['sources_used'].append({
            'type': 'youtube', 'title': t['video_id'], 'url': t['url']
        })
    for ws in web_sources:
        sections['sources_used'].append({
            'type': 'web', 'title': ws['title'], 'url': ws['url']
        })

    processing_time = round(time.time() - start_time, 1)

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
            'processing_time': processing_time,
            'failed_urls': failed_urls
        },
        'usage': final_result.get('usage', {})
    }


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
