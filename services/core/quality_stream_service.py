"""검토된 본문만 노출하며 진행 상태와 취소를 전달하는 품질 스트림."""
from queue import Empty, Queue
from threading import Event, Thread
from contextlib import nullcontext

from services.core.content_quality_service import generate_verified


class QualityGenerationCancelled(Exception):
    """연결이 종료됐으므로 다음 모델 호출을 시작하지 않는다."""


def stream_verified(*args, worker_context=nullcontext, **kwargs):
    cancelled = Event()
    events = Queue()

    def check_cancelled():
        if cancelled.is_set():
            raise QualityGenerationCancelled()

    def progress(stage):
        check_cancelled()
        events.put(('status', stage))

    def run():
        try:
            with (worker_context or nullcontext)():
                result = generate_verified(*args, **kwargs, on_progress=progress,
                                           check_cancelled=check_cancelled)
                check_cancelled()
                events.put(('result', result))
        except QualityGenerationCancelled:
            pass
        except Exception as error:
            events.put(('error', error))

    # 닫힌 연결을 위해 새 호출을 하지 않는다. 이미 실행 중인 공급자 요청은
    # 해당 요청의 제한 시간(최대 60초) 안에 종료된 뒤 결과를 버린다.
    worker = Thread(target=run, name='luna-quality', daemon=True)
    worker.start()
    stage = 'evidence'
    try:
        while True:
            try:
                kind, value = events.get(timeout=5)
            except Empty:
                # 정기 전송으로 연결 종료를 감지하고 중간 연결의 유휴 종료를 막는다.
                yield {'type': 'status', 'stage': stage}
                continue
            if kind == 'error':
                raise value
            if kind == 'result':
                return value
            stage = value
            yield {'type': 'status', 'stage': stage}
    finally:
        cancelled.set()
