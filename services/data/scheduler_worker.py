"""
예약 발행 + 채널 모니터링 백그라운드 워커

APScheduler로 매분 예약된 포스트를 확인하고 MCP 플러그인으로 발행합니다.
채널 모니터링은 30분 간격으로 신규 업로드를 감지합니다.
"""
from apscheduler.schedulers.background import BackgroundScheduler

from services.core.logging_config import get_logger
import logging

logger = get_logger('scheduler_worker')

scheduler = BackgroundScheduler()


def check_and_publish():
    """매분 실행: 예약된 포스트 확인 → MCP 발행"""
    try:
        from services.data.schedule_service import schedule_service
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
    except Exception as e:
        logger.error("check_and_publish 실패: %s", e, exc_info=True)
        return None


def _check_channel_monitors():
    """30분 간격: 채널 모니터링 → 신규 영상 감지 시 로깅"""
    from services.data.supabase_service import get_supabase, is_supabase_enabled
    from services.platform.channel_monitor_service import check_monitors

    if not is_supabase_enabled():
        return

    try:
        client = get_supabase()
        new_videos = check_monitors(client)
        if new_videos:
            logger.info(f"채널 모니터링: 신규 영상 {len(new_videos)}건 감지")
            for video in new_videos:
                logger.info(
                    f"  - 채널 {video['channel_id']}: "
                    f"{video['title']} (video_id={video['video_id']})"
                )
    except Exception as e:
        logger.error(f"채널 모니터링 실패: {e}")


def _process_publish_queue():
    """2분 간격: 발행 큐 대기 항목 처리"""
    from services.data.publish_queue_service import publish_queue_service

    try:
        results = publish_queue_service.process_queue()
        if results:
            logger.info(f"발행 큐 처리 완료: {len(results)}건")
    except Exception as e:
        logger.error(f"발행 큐 처리 실패: {e}")


def _check_rss_subscriptions():
    """30분 간격: RSS 구독 피드 새 글 감지"""
    from services.platform.rss_subscription_service import check_all_subscriptions

    try:
        results = check_all_subscriptions()
        if results:
            for r in results:
                feed_title = r['subscription'].get('title', '알 수 없음')
                count = len(r['new_entries'])
                logger.info(f"RSS 새 글 감지: {feed_title} — {count}건 (user={r['user_id']})")
    except Exception as e:
        logger.error(f"RSS 구독 확인 실패: {e}")


def start_scheduler(app):
    """Flask 앱 컨텍스트에서 스케줄러 시작"""
    try:
        if scheduler.running:
            return

        _app = app  # 클로저 캡처

        def _with_context(func):
            """Flask 앱 컨텍스트 내에서 job 함수를 실행하는 래퍼"""
            def wrapper():
                with _app.app_context():
                    func()
            wrapper.__name__ = func.__name__
            return wrapper

        scheduler.add_job(
            _with_context(check_and_publish),
            'interval',
            minutes=1,
            id='publish_checker',
            replace_existing=True,
        )
        scheduler.add_job(
            _with_context(_check_channel_monitors),
            'interval',
            minutes=30,
            id='channel_monitor_checker',
            replace_existing=True,
        )
        scheduler.add_job(
            _with_context(_process_publish_queue),
            'interval',
            minutes=2,
            id='publish_queue_processor',
            replace_existing=True,
        )
        scheduler.add_job(
            _with_context(_check_rss_subscriptions),
            'interval',
            minutes=30,
            id='rss_subscription_checker',
            replace_existing=True,
        )
        scheduler.start()
        logger.info("스케줄러 시작됨 (예약 발행: 1분, 채널 모니터링: 30분, 발행 큐: 2분, RSS 구독: 30분)")
    except Exception as e:
        logger.error("start_scheduler 실패: %s", e, exc_info=True)
        return None


def stop_scheduler():
    """스케줄러 종료"""
    try:
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("예약 발행 스케줄러 종료됨")
    except Exception as e:
        logger.error("stop_scheduler 실패: %s", e, exc_info=True)
        return None
