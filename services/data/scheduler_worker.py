"""
예약 발행 + 채널 모니터링 백그라운드 워커

APScheduler로 매분 예약된 포스트를 확인하고 MCP 플러그인으로 발행합니다.
채널 모니터링은 30분 간격으로 신규 업로드를 감지합니다.

apscheduler import는 entry-points 전체 스캔으로 ~0.7초가 걸려 앱 스타트업의
약 31%를 차지하므로, 스케줄러 인스턴스는 PEP 562 __getattr__로 지연 생성한다.
(외부에서 `from ... import scheduler`로 접근하는 기존 코드/테스트와 호환)
"""
import fcntl
import os
from pathlib import Path
from datetime import datetime, timezone

from services.core.logging_config import get_logger

logger = get_logger('scheduler_worker')

_scheduler = None
_scheduler_lock_file = None


def _truthy(value: str | None) -> bool:
    return (value or '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _scheduler_heartbeat_path() -> Path | None:
    raw = os.getenv('SCHEDULER_HEARTBEAT_FILE', '').strip()
    return Path(raw) if raw else None


def _scheduler_heartbeat_interval_seconds() -> int:
    raw = os.getenv('SCHEDULER_HEARTBEAT_INTERVAL_SECONDS', '30').strip()
    try:
        interval = int(raw)
    except ValueError:
        logger.warning('SCHEDULER_HEARTBEAT_INTERVAL_SECONDS 값이 정수가 아님: %s', raw)
        return 30
    if interval < 5:
        logger.warning('SCHEDULER_HEARTBEAT_INTERVAL_SECONDS 값이 5보다 작음: %s', raw)
        return 30
    return interval


def write_scheduler_heartbeat(path: str | Path | None = None) -> None:
    """스케줄러 생존 heartbeat 파일을 갱신한다."""
    target = Path(path) if path else _scheduler_heartbeat_path()
    if target is None:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), encoding='utf-8')


def _acquire_scheduler_leader_lock() -> bool:
    """gunicorn 다중 worker 환경에서 스케줄러를 단일 프로세스만 실행하게 한다."""
    global _scheduler_lock_file
    if _scheduler_lock_file is not None:
        return True

    lock_path = Path(os.getenv('SCHEDULER_LOCK_FILE', '/tmp/insight-engine-scheduler.lock'))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = lock_path.open('w')
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_file.close()
        return False

    lock_file.write(str(os.getpid()))
    lock_file.truncate()
    lock_file.flush()
    _scheduler_lock_file = lock_file
    return True


def _release_scheduler_leader_lock() -> None:
    """stop_scheduler에서 리더락을 해제한다."""
    global _scheduler_lock_file
    if _scheduler_lock_file is None:
        return
    try:
        fcntl.flock(_scheduler_lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        _scheduler_lock_file.close()
        _scheduler_lock_file = None


def _get_scheduler():
    """BackgroundScheduler를 최초 접근 시점에 생성한다."""
    global _scheduler
    if _scheduler is None:
        from apscheduler.schedulers.background import BackgroundScheduler
        _scheduler = BackgroundScheduler()
    return _scheduler


def __getattr__(name):
    if name == 'scheduler':
        return _get_scheduler()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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


def _backup_app_data():
    """설정된 간격으로 app_data 볼륨 백업을 생성한다."""
    backup_dir = os.getenv('APP_DATA_BACKUP_DIR', '').strip()
    if not backup_dir:
        logger.warning('APP_DATA_BACKUP_DIR 미설정 — app_data 자동 백업 생략')
        return

    from utils.app_data_backup import create_app_data_backup

    source_dir = os.getenv('APP_DATA_DIR', 'data')
    max_backups = _max_backups()
    replica_dir = os.getenv('APP_DATA_BACKUP_REPLICA_DIR', '').strip() or None
    max_replica_backups = _max_replica_backups()
    try:
        payload = create_app_data_backup(
            source_dir,
            backup_dir,
            max_backups=max_backups,
            replica_dir=replica_dir,
            max_replica_backups=max_replica_backups,
        )
        replica = payload.get('replica') or {}
        logger.info(
            'app_data 백업 완료: %s (%s files, %s bytes, pruned=%s, replica=%s)',
            payload.get('archive_path'),
            payload.get('file_count'),
            payload.get('size_bytes'),
            len(payload.get('pruned_archive_paths') or []),
            replica.get('replica_path') or 'disabled',
        )
    except FileNotFoundError:
        logger.warning('app_data 백업 소스가 없어 생략: %s', source_dir)
    except Exception as e:
        logger.error('app_data 자동 백업 실패: %s', e, exc_info=True)


def _backup_interval_hours() -> int | None:
    raw = os.getenv('AUTO_BACKUP_INTERVAL_HOURS', '').strip()
    if not raw:
        return None
    try:
        interval = int(raw)
    except ValueError:
        logger.warning('AUTO_BACKUP_INTERVAL_HOURS 값이 정수가 아님: %s', raw)
        return None
    if interval < 1:
        logger.warning('AUTO_BACKUP_INTERVAL_HOURS 값이 1보다 작음: %s', raw)
        return None
    return interval


def _max_backups() -> int | None:
    raw = os.getenv('MAX_BACKUPS', '').strip()
    if not raw:
        return None
    try:
        max_backups = int(raw)
    except ValueError:
        logger.warning('MAX_BACKUPS 값이 정수가 아님: %s', raw)
        return None
    if max_backups < 1:
        logger.warning('MAX_BACKUPS 값이 1보다 작음: %s', raw)
        return None
    return max_backups


def _max_replica_backups() -> int | None:
    raw = os.getenv('APP_DATA_BACKUP_REPLICA_MAX_BACKUPS', '').strip()
    if not raw:
        return _max_backups()
    try:
        max_backups = int(raw)
    except ValueError:
        logger.warning('APP_DATA_BACKUP_REPLICA_MAX_BACKUPS 값이 정수가 아님: %s', raw)
        return _max_backups()
    if max_backups < 1:
        logger.warning('APP_DATA_BACKUP_REPLICA_MAX_BACKUPS 값이 1보다 작음: %s', raw)
        return _max_backups()
    return max_backups


def start_scheduler(app):
    """Flask 앱 컨텍스트에서 스케줄러 시작"""
    try:
        # 테스트/스크립트 등에서 스케줄러 기동을 끌 수 있는 게이트
        if not _truthy(os.getenv('SCHEDULER_ENABLED') or 'true'):
            logger.info("SCHEDULER_ENABLED=false — 스케줄러 기동 생략")
            return

        # gunicorn --workers=2 이상에서는 각 worker가 app.py를 import하므로
        # APScheduler도 worker 수만큼 뜰 수 있다. 파일락으로 컨테이너 내 1개만 실행한다.
        if not _acquire_scheduler_leader_lock():
            logger.info('다른 worker가 스케줄러 리더락을 보유 중 — 스케줄러 기동 생략')
            return

        # 모듈 자기참조로 접근해야 테스트의 scheduler patch와 지연 생성이 모두 동작한다
        import services.data.scheduler_worker as _self
        scheduler = _self.scheduler
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

        heartbeat_path = _scheduler_heartbeat_path()
        if heartbeat_path:
            write_scheduler_heartbeat(heartbeat_path)
            scheduler.add_job(
                write_scheduler_heartbeat,
                'interval',
                seconds=_scheduler_heartbeat_interval_seconds(),
                id='scheduler_heartbeat',
                replace_existing=True,
            )
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
        backup_interval = _backup_interval_hours()
        if backup_interval:
            scheduler.add_job(
                _with_context(_backup_app_data),
                'interval',
                hours=backup_interval,
                id='app_data_backup',
                replace_existing=True,
            )
        scheduler.start()
        logger.info(
            "스케줄러 시작됨 (예약 발행: 1분, 채널 모니터링: 30분, 발행 큐: 2분, RSS 구독: 30분, app_data 백업: %s)",
            f"{backup_interval}시간" if backup_interval else "비활성",
        )
    except Exception as e:
        logger.error("start_scheduler 실패: %s", e, exc_info=True)
        return None


def stop_scheduler():
    """스케줄러 종료"""
    try:
        # 생성된 적이 없으면 종료할 것도 없다 (불필요한 지연 생성 방지)
        import services.data.scheduler_worker as _self
        if _self._scheduler is None and 'scheduler' not in _self.__dict__:
            _release_scheduler_leader_lock()
            return
        scheduler = _self.scheduler
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("예약 발행 스케줄러 종료됨")
        _release_scheduler_leader_lock()
    except Exception as e:
        logger.error("stop_scheduler 실패: %s", e, exc_info=True)
        return None
