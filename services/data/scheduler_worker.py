"""
채널 모니터링 백그라운드 워커

예약 발행/RSS 구독 확인 기능은 제거됨(Dep-6/Dep-14). 채널 모니터링은
30분 간격으로 신규 업로드를 감지합니다.

apscheduler import는 entry-points 전체 스캔으로 ~0.7초가 걸려 앱 스타트업의
약 31%를 차지하므로, 스케줄러 인스턴스는 PEP 562 __getattr__로 지연 생성합니다.
(테스트에서 `from ... import scheduler`로 접근하는 기존 코드/테스트와 호환)
"""

import os
import stat
import tempfile
from pathlib import Path

try:
    import fcntl  # Unix 전용 — gunicorn 다중 worker 리더락(flock)에만 사용
except ImportError:  # Windows 등 fcntl 미지원 환경 (단일 프로세스 개발/실행)
    fcntl = None

from services.core.logging_config import get_logger

logger = get_logger("scheduler_worker")

_scheduler = None
_scheduler_lock_file = None


def _default_scheduler_lock_path() -> Path:
    """Return a per-user private runtime path instead of a shared /tmp file."""
    user_id = os.geteuid() if hasattr(os, 'geteuid') else os.getpid()
    return Path(tempfile.gettempdir()) / f'insight-engine-{user_id}' / 'scheduler.lock'


def _acquire_scheduler_leader_lock() -> bool:
    """gunicorn 다중 worker 환경에서 스케줄러를 단일 프로세스만 실행하게 한다."""
    global _scheduler_lock_file
    if _scheduler_lock_file is not None:
        return True

    if fcntl is None:
        # Windows 등 flock 미지원 환경: 단일 프로세스로 간주하고 항상 리더로 동작
        _scheduler_lock_file = True
        return True

    configured_path = (os.getenv('SCHEDULER_LOCK_FILE') or '').strip()
    lock_path = Path(configured_path) if configured_path else _default_scheduler_lock_path()
    lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)

    flags = os.O_RDWR | os.O_CREAT
    flags |= getattr(os, 'O_CLOEXEC', 0)
    flags |= getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise RuntimeError('scheduler lock path must be a regular file')
        os.fchmod(descriptor, 0o600)
    except Exception:
        os.close(descriptor)
        raise
    lock_file = os.fdopen(descriptor, 'w')
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
    if fcntl is None:
        # flock 미지원 환경에서는 센티넬만 해제
        _scheduler_lock_file = None
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
    if name == "scheduler":
        return _get_scheduler()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _check_channel_monitors():
    """30분 간격: 채널 모니터링 → 신규 영상 감지 시 로깅"""
    from services.data.supabase_service import (
        get_service_supabase,
        is_supabase_enabled,
    )
    from services.platform.channel_monitor_service import check_monitors

    if not is_supabase_enabled():
        return

    try:
        # 스케줄러는 사용자 요청/JWT 밖에서 모든 활성 모니터를 조회한다.
        # anon 폴백은 RLS 때문에 조용히 빈 결과를 만들 수 있으므로 서버 전용
        # service-role 클라이언트를 명시하고, 설정 누락 시 실패 폐쇄한다.
        client = get_service_supabase()
        if client is None:
            logger.error("채널 모니터링 실패: service-role client unavailable")
            return
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


def start_scheduler(app):
    """Flask 앱 컨텍스트에서 스케줄러 시작"""
    try:
        # 테스트/스크립트 등에서 스케줄러 기동을 끌 수 있는 게이트
        if os.getenv("SCHEDULER_ENABLED", "true").lower() not in ("true", "1", "yes"):
            logger.info("SCHEDULER_ENABLED=false — 스케줄러 기동 생략")
            return

        # gunicorn --workers=2 이상에서는 각 worker가 app.py를 import하므로
        # APScheduler도 worker 수만큼 뜰 수 있다. 파일락으로 컨테이너 내 1개만 실행한다.
        if not _acquire_scheduler_leader_lock():
            logger.info("다른 worker가 스케줄러 리더락을 보유 중 — 스케줄러 기동 생략")
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

        scheduler.add_job(
            _with_context(_check_channel_monitors),
            "interval",
            minutes=30,
            id="channel_monitor_checker",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("스케줄러 시작됨 (채널 모니터링: 30분)")
    except Exception as e:
        logger.error("start_scheduler 실패: %s", e, exc_info=True)
        return None


def stop_scheduler():
    """스케줄러 종료"""
    try:
        # 생성된 적이 없으면 종료할 것도 없다 (불필요한 지연 생성 방지)
        import services.data.scheduler_worker as _self

        if _self._scheduler is None and "scheduler" not in _self.__dict__:
            _release_scheduler_leader_lock()
            return
        scheduler = _self.scheduler
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("스케줄러 종료됨")
        _release_scheduler_leader_lock()
    except Exception as e:
        logger.error("stop_scheduler 실패: %s", e, exc_info=True)
        return None
