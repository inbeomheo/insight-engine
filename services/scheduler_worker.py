"""
예약 발행 백그라운드 워커

APScheduler로 매분 예약된 포스트를 확인하고 MCP 플러그인으로 발행합니다.
"""
from apscheduler.schedulers.background import BackgroundScheduler

from services.logging_config import get_logger

logger = get_logger('scheduler_worker')

scheduler = BackgroundScheduler()


def check_and_publish():
    """매분 실행: 예약된 포스트 확인 → MCP 발행"""
    from services.schedule_service import schedule_service
    from services.mcp import plugin_registry

    due_posts = schedule_service.get_due_posts()
    if not due_posts:
        return

    logger.info(f"발행 대기 포스트 {len(due_posts)}건 처리 시작")

    for post in due_posts:
        post_id = post['id']
        try:
            result = plugin_registry.execute(
                post['target_plugin'],
                post['content'],
                post['title'],
            )
            if result.get('success'):
                schedule_service.update_status(
                    post_id, 'published',
                    published_url=result.get('url'),
                )
                logger.info(f"발행 완료: {post_id}")
            else:
                schedule_service.update_status(
                    post_id, 'failed',
                    error_message=result.get('message', '발행 실패'),
                )
                logger.warning(f"발행 실패: {post_id} - {result.get('message')}")
        except Exception as e:
            schedule_service.update_status(post_id, 'failed', error_message=str(e))
            logger.error(f"발행 예외: {post_id} - {e}")


def start_scheduler(app):
    """Flask 앱 컨텍스트에서 스케줄러 시작"""
    if scheduler.running:
        return

    scheduler.add_job(
        check_and_publish,
        'interval',
        minutes=1,
        id='publish_checker',
        replace_existing=True,
    )
    scheduler.start()
    logger.info("예약 발행 스케줄러 시작됨 (매 1분 간격)")


def stop_scheduler():
    """스케줄러 종료"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("예약 발행 스케줄러 종료됨")
