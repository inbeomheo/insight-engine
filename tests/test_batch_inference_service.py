"""비동기 배치 추론 서비스 테스트"""
import time
import pytest
from unittest.mock import patch
from services.batch_inference_service import (
    submit_batch,
    get_batch_status,
    get_batch_results,
    cancel_batch,
    list_batches,
    cleanup_old_batches,
    BatchStatus,
    _clear_store,
    _batch_store,
)


@pytest.fixture(autouse=True)
def clean_store():
    """각 테스트 전후 저장소 초기화"""
    _clear_store()
    yield
    _clear_store()


class TestSubmitBatch:
    """배치 제출 테스트"""

    def test_submit_batch(self):
        """배치 제출 시 batch_id가 반환되고 저장소에 등록된다"""
        requests = [
            {"url": "https://youtube.com/watch?v=abc", "style_id": "blog_seo"},
            {"url": "https://youtube.com/watch?v=def", "style_id": "summary"},
        ]
        batch_id = submit_batch(requests, run_sync=True)

        assert batch_id is not None
        assert len(batch_id) == 36  # UUID 형식
        assert batch_id in _batch_store

    def test_submit_batch_empty(self):
        """빈 요청 목록 제출 시 ValueError 발생"""
        with pytest.raises(ValueError, match="요청 목록이 비어있습니다"):
            submit_batch([])

    def test_submit_batch_single(self):
        """단일 요청 배치가 정상 처리된다"""
        requests = [{"url": "https://youtube.com/watch?v=single"}]
        batch_id = submit_batch(requests, run_sync=True)

        status = get_batch_status(batch_id)
        assert status["total"] == 1
        assert status["completed"] == 1
        assert status["status"] == "completed"


class TestGetBatchStatus:
    """배치 상태 조회 테스트"""

    def test_get_batch_status_pending(self):
        """제출 직후 대기 상태를 확인한다 (동기 실행 전)"""
        # run_sync=False로 제출하되, 처리 전에 상태 확인
        # 스레드가 시작되기 전 상태를 캡처하기 위해 _run_batch를 모킹
        with patch('services.batch_inference_service._run_batch'):
            requests = [{"url": "https://youtube.com/watch?v=abc"}]
            batch_id = submit_batch(requests, run_sync=False)

        status = get_batch_status(batch_id)
        assert status["status"] == "pending"
        assert status["progress"] == 0
        assert status["total"] == 1
        assert status["completed"] == 0

    def test_get_batch_status_not_found(self):
        """존재하지 않는 batch_id 조회 시 KeyError 발생"""
        with pytest.raises(KeyError, match="배치를 찾을 수 없습니다"):
            get_batch_status("nonexistent-id")


class TestGetBatchResults:
    """배치 결과 조회 테스트"""

    def test_get_batch_results_empty(self):
        """미완료 배치의 결과는 모두 pending 상태이다"""
        with patch('services.batch_inference_service._run_batch'):
            requests = [
                {"url": "https://youtube.com/watch?v=a"},
                {"url": "https://youtube.com/watch?v=b"},
            ]
            batch_id = submit_batch(requests, run_sync=False)

        results = get_batch_results(batch_id)
        assert len(results) == 2
        assert all(r["status"] == "pending" for r in results)
        assert all(r["result"] is None for r in results)

    def test_get_batch_results_completed(self):
        """완료된 배치의 결과를 정상 수집한다"""
        requests = [
            {"url": "https://youtube.com/watch?v=a", "style_id": "blog_seo"},
            {"url": "https://youtube.com/watch?v=b", "style_id": "summary"},
        ]
        batch_id = submit_batch(requests, run_sync=True)

        results = get_batch_results(batch_id)
        assert len(results) == 2
        assert all(r["status"] == "completed" for r in results)
        assert results[0]["result"]["style_id"] == "blog_seo"
        assert results[1]["result"]["style_id"] == "summary"

    def test_get_batch_results_not_found(self):
        """존재하지 않는 배치 결과 조회 시 KeyError"""
        with pytest.raises(KeyError):
            get_batch_results("no-such-id")


class TestCancelBatch:
    """배치 취소 테스트"""

    def test_cancel_batch(self):
        """대기 중인 배치를 취소한다"""
        with patch('services.batch_inference_service._run_batch'):
            requests = [
                {"url": "https://youtube.com/watch?v=a"},
                {"url": "https://youtube.com/watch?v=b"},
            ]
            batch_id = submit_batch(requests, run_sync=False)

        result = cancel_batch(batch_id)
        assert result is True

        status = get_batch_status(batch_id)
        assert status["status"] == "cancelled"

    def test_cancel_batch_not_found(self):
        """존재하지 않는 배치 취소 시 KeyError"""
        with pytest.raises(KeyError, match="배치를 찾을 수 없습니다"):
            cancel_batch("nonexistent-id")

    def test_cancel_batch_completed(self):
        """이미 완료된 배치 취소 시 False 반환"""
        requests = [{"url": "https://youtube.com/watch?v=a"}]
        batch_id = submit_batch(requests, run_sync=True)

        result = cancel_batch(batch_id)
        assert result is False


class TestListBatches:
    """배치 목록 조회 테스트"""

    def test_list_batches(self):
        """전체 배치 목록을 반환한다"""
        submit_batch([{"url": "https://youtube.com/watch?v=1"}], run_sync=True)
        submit_batch([{"url": "https://youtube.com/watch?v=2"}], run_sync=True)

        batches = list_batches()
        assert len(batches) == 2
        assert all("batch_id" in b for b in batches)
        assert all("status" in b for b in batches)

    def test_list_batches_by_status(self):
        """상태별 필터링이 동작한다"""
        # 완료 배치 1개
        submit_batch([{"url": "https://youtube.com/watch?v=1"}], run_sync=True)

        # 대기 배치 1개
        with patch('services.batch_inference_service._run_batch'):
            submit_batch([{"url": "https://youtube.com/watch?v=2"}], run_sync=False)

        completed = list_batches(status="completed")
        pending = list_batches(status="pending")

        assert len(completed) == 1
        assert len(pending) == 1
        assert completed[0]["status"] == "completed"
        assert pending[0]["status"] == "pending"

    def test_list_batches_empty(self):
        """배치가 없으면 빈 리스트 반환"""
        batches = list_batches()
        assert batches == []


class TestCleanupOldBatches:
    """오래된 배치 정리 테스트"""

    def test_cleanup_old_batches(self):
        """오래된 완료 배치를 정리한다"""
        # 오래된 배치 생성
        batch_id = submit_batch(
            [{"url": "https://youtube.com/watch?v=old"}], run_sync=True
        )

        # created_at을 25시간 전으로 조작
        _batch_store[batch_id].created_at = time.time() - (25 * 3600)

        removed = cleanup_old_batches(max_age_hours=24)
        assert removed == 1
        assert batch_id not in _batch_store

    def test_cleanup_preserves_recent(self):
        """최근 배치는 정리하지 않는다"""
        batch_id = submit_batch(
            [{"url": "https://youtube.com/watch?v=recent"}], run_sync=True
        )

        removed = cleanup_old_batches(max_age_hours=24)
        assert removed == 0
        assert batch_id in _batch_store

    def test_cleanup_preserves_processing(self):
        """처리 중인 배치는 오래되어도 정리하지 않는다"""
        with patch('services.batch_inference_service._run_batch'):
            batch_id = submit_batch(
                [{"url": "https://youtube.com/watch?v=proc"}], run_sync=False
            )

        # created_at을 25시간 전으로 조작, 상태는 PENDING (진행 전)
        # PENDING은 종료 상태가 아니므로 정리 대상 아님
        _batch_store[batch_id].created_at = time.time() - (25 * 3600)

        removed = cleanup_old_batches(max_age_hours=24)
        assert removed == 0


class TestBatchProgress:
    """진행률 계산 테스트"""

    def test_batch_progress(self):
        """동기 처리 완료 후 진행률이 100%이다"""
        requests = [
            {"url": "https://youtube.com/watch?v=1"},
            {"url": "https://youtube.com/watch?v=2"},
            {"url": "https://youtube.com/watch?v=3"},
            {"url": "https://youtube.com/watch?v=4"},
        ]
        batch_id = submit_batch(requests, run_sync=True)

        status = get_batch_status(batch_id)
        assert status["progress"] == 100
        assert status["completed"] == 4
        assert status["total"] == 4

    def test_batch_default_style(self):
        """style_id 미지정 시 기본값 blog_seo가 적용된다"""
        batch_id = submit_batch(
            [{"url": "https://youtube.com/watch?v=no_style"}], run_sync=True
        )

        results = get_batch_results(batch_id)
        assert results[0]["style_id"] == "blog_seo"
        assert results[0]["result"]["style_id"] == "blog_seo"
