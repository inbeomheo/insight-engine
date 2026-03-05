"""
콘텐츠 생성 워커 (F9-02)
TaskQueueService를 통해 비동기 콘텐츠 생성 처리
"""
import logging
import os
import sys

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.task_queue_service import get_task_queue

logger = logging.getLogger(__name__)


def generate_content_async(
    url: str,
    style_id: str,
    model: str,
    length: str = 'medium',
    writing_style: str = 'conversational',
    language: str = 'ko',
    user_id: str = '',
) -> str:
    """
    비동기 콘텐츠 생성 태스크 등록

    Returns:
        task_id — 나중에 poll로 결과 확인 가능
    """
    queue = get_task_queue()
    task_id = queue.enqueue(
        _do_generate,
        url=url,
        style_id=style_id,
        model=model,
        length=length,
        writing_style=writing_style,
        language=language,
        user_id=user_id,
        priority=1,
    )
    logger.info("비동기 생성 태스크 등록: %s (url=%s, style=%s)", task_id, url[:50], style_id)
    return task_id


def _do_generate(
    url: str,
    style_id: str,
    model: str,
    length: str,
    writing_style: str,
    language: str,
    user_id: str,
) -> dict:
    """
    실제 콘텐츠 생성 작업 (워커 스레드에서 실행)
    """
    from services.content_service import ContentService
    from services.ai_service import create_content

    logger.info("콘텐츠 생성 워커 시작: url=%s", url[:50])

    # 자막 추출
    content_svc = ContentService()
    transcript_result = content_svc.get_transcript(url)

    if not transcript_result.get('transcript'):
        raise ValueError(f"자막 추출 실패: {transcript_result.get('error', '알 수 없는 오류')}")

    # AI 콘텐츠 생성
    result = create_content(
        transcript=transcript_result['transcript'],
        style_id=style_id,
        model=model,
        length=length,
        writing_style=writing_style,
        language=language,
    )

    logger.info("콘텐츠 생성 워커 완료: url=%s, style=%s", url[:50], style_id)
    return result


def get_task_result(task_id: str) -> dict:
    """태스크 결과 조회"""
    queue = get_task_queue()
    result = queue.get_task(task_id)
    if not result:
        return {'error': f'태스크를 찾을 수 없습니다: {task_id}'}
    return result
