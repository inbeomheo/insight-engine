"""publish_queue 멀티 프로세스 안전성 검증

backend 워커와 scheduler 컨테이너 간 race condition을 file lock + reload로 해결.
"""
import json
import os
import shutil
import tempfile
import unittest


class TestMultiProcessSafety(unittest.TestCase):
    """파일 락 + reload 패턴이 멀티 프로세스 시뮬레이션에서 안전한지 검증"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="ie_pq_mp_")
        # 모듈 경로 swap
        import services.data.publish_queue_service as pq
        self._orig_file = pq.QUEUE_FILE
        self._orig_lock = pq.QUEUE_LOCK_FILE
        pq.QUEUE_FILE = os.path.join(self.tmpdir, 'publish_queue.json')
        pq.QUEUE_LOCK_FILE = pq.QUEUE_FILE + '.lock'
        self.pq_module = pq

    def tearDown(self):
        self.pq_module.QUEUE_FILE = self._orig_file
        self.pq_module.QUEUE_LOCK_FILE = self._orig_lock
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _fresh_service(self):
        """새 서비스 인스턴스 생성 — 다른 워커 프로세스 시뮬레이션"""
        from services.data.publish_queue_service import PublishQueueService
        return PublishQueueService()

    def test_writes_from_different_instances_are_persisted(self):
        """워커 A의 enqueue를 워커 B가 process_queue에서 볼 수 있어야 함"""
        worker_a = self._fresh_service()
        worker_b = self._fresh_service()

        # 워커 A에서 큐 추가
        result_a = worker_a.enqueue(
            content_id='c1', title='제목', content='본문',
            plugin_id='wp', user_id='u1',
        )
        self.assertTrue(result_a.get('id'))

        # 워커 B는 초기화 시점에 파일이 비어있었으므로 in-memory 큐가 비어있음
        # → reload를 통해 워커 A의 enqueue를 볼 수 있어야 함
        status_before_reload = worker_b.get_queue_status()
        # get_queue_status는 reload를 안 하므로 워커 B는 못 봄
        self.assertEqual(len(status_before_reload), 0)

        # 워커 B가 enqueue를 호출하면 내부에서 reload → 워커 A 항목 + 새 항목 모두 보존
        worker_b.enqueue(
            content_id='c2', title='제목2', content='본문2',
            plugin_id='wp', user_id='u1',
        )
        # 디스크에서 직접 확인 — 두 항목 모두 존재
        with open(self.pq_module.QUEUE_FILE, 'r', encoding='utf-8') as f:
            on_disk = json.load(f)
        self.assertEqual(len(on_disk), 2)
        content_ids = {item['content_id'] for item in on_disk}
        self.assertEqual(content_ids, {'c1', 'c2'})

    def test_cancel_from_other_worker(self):
        """워커 A가 enqueue한 항목을 워커 B가 cancel — 두 워커 모두 결과 일관성"""
        worker_a = self._fresh_service()
        worker_b = self._fresh_service()

        item = worker_a.enqueue('c1', '제목', '본문', 'wp', 'u1')
        item_id = item['id']

        # 워커 B에서 취소 (reload 후 처리)
        result = worker_b.cancel_item(item_id)
        self.assertTrue(result.get('success'))

        # 디스크에서 제거 확인
        with open(self.pq_module.QUEUE_FILE, 'r', encoding='utf-8') as f:
            on_disk = json.load(f)
        self.assertEqual(len(on_disk), 0)

    def test_file_lock_serializes_writes(self):
        """파일 락이 잡혀있을 때 다른 프로세스는 timeout까지 대기"""
        from filelock import FileLock, Timeout
        # 외부 락을 짧은 timeout으로 가져옴
        external = FileLock(self.pq_module.QUEUE_LOCK_FILE, timeout=0.1)
        with external:
            # 새 서비스가 enqueue 시도 — 락 보유한 상태에서 5초 timeout 내에 실패해야 함
            worker = self._fresh_service()
            # FILELOCK_TIMEOUT을 매우 짧게 패치하여 빠른 실패 유도
            self.pq_module.FILELOCK_TIMEOUT = 0.2
            # 재구성: file_lock 객체를 timeout 0.2로 재생성
            from filelock import FileLock as FL
            worker._file_lock = FL(self.pq_module.QUEUE_LOCK_FILE, timeout=0.2)
            result = worker.enqueue('c1', 't', 'b', 'wp', 'u1')
            # timeout으로 인해 빈 dict 반환
            self.assertEqual(result, {})


if __name__ == '__main__':
    unittest.main()
