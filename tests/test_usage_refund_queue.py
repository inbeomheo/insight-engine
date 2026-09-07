"""Durable quota-refund reconciliation regression tests."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from services.usage.refund_queue import (
    RefundQueueCapacityExceeded,
    enqueue_refund,
    pending_refund_count,
    pending_refunds_for_user,
)
from services.usage.usage_service import (
    UsageAccountingUnavailable,
    UsageService,
)
from tests.test_usage_service import _make_reservation


def test_failed_refund_is_persisted_and_reconciled_after_recovery():
    reservation = _make_reservation()
    with tempfile.TemporaryDirectory() as directory:
        queue_path = Path(directory) / 'refunds.json'
        with (
            patch.dict(os.environ, {'USAGE_REFUND_QUEUE_PATH': str(queue_path)}),
            patch('services.usage.usage_service._get_account_repository'),
            patch('services.usage.usage_service.mark_usage_accounting_unavailable'),
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.'
                'SupabaseUsageGateway.refund',
                side_effect=OSError('database unavailable'),
            ),
        ):
            with pytest.raises(UsageAccountingUnavailable):
                UsageService.refund_reservation('user-1', reservation)
            assert pending_refund_count('user-1') == 1
            assert queue_path.stat().st_mode & 0o077 == 0

        with (
            patch.dict(os.environ, {'USAGE_REFUND_QUEUE_PATH': str(queue_path)}),
            patch('services.usage.usage_service._get_account_repository'),
            patch('services.usage.usage_service.mark_usage_accounting_unavailable'),
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.'
                'SupabaseUsageGateway.refund',
                return_value=3,
            ) as refund,
        ):
            assert UsageService.reconcile_pending_refunds('user-1') == 1
            assert pending_refund_count('user-1') == 0
            refunded_quota = refund.call_args.args[1]
            assert refunded_quota.reservation_id == reservation.quota.reservation_id
            assert refunded_quota.owner_token_hash == reservation.quota.owner_token_hash


def test_pending_refund_for_another_user_is_not_reconciled():
    reservation = _make_reservation()
    with tempfile.TemporaryDirectory() as directory:
        queue_path = Path(directory) / 'refunds.json'
        with (
            patch.dict(os.environ, {'USAGE_REFUND_QUEUE_PATH': str(queue_path)}),
            patch('services.usage.usage_service._get_account_repository'),
            patch('services.usage.usage_service.mark_usage_accounting_unavailable'),
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.'
                'SupabaseUsageGateway.refund',
                side_effect=OSError('database unavailable'),
            ),
        ):
            with pytest.raises(UsageAccountingUnavailable):
                UsageService.refund_reservation('user-a', reservation)

        with (
            patch.dict(os.environ, {'USAGE_REFUND_QUEUE_PATH': str(queue_path)}),
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.'
                'SupabaseUsageGateway.refund',
            ) as refund,
        ):
            assert UsageService.reconcile_pending_refunds('user-b') == 0
            refund.assert_not_called()
            assert pending_refund_count('user-a') == 1


def test_new_reservation_fails_closed_when_reconciliation_cannot_complete():
    with (
        patch('services.usage.usage_service.is_supabase_enabled', return_value=True),
        patch('services.usage.usage_service._is_admin_cached', return_value=False),
        patch.object(
            UsageService,
            'reconcile_pending_refunds',
            side_effect=UsageAccountingUnavailable('refund backend unavailable'),
        ) as reconcile,
        patch(
            'src.contexts.identity.infrastructure.supabase_usage_gateway.'
            'SupabaseUsageGateway.reserve',
        ) as reserve,
    ):
        with pytest.raises(UsageAccountingUnavailable):
            UsageService.reserve_for_request('user-1')

    reconcile.assert_called_once_with('user-1')
    reserve.assert_not_called()


def _refund_job(reservation_id: str = 'reservation-1') -> dict:
    return {
        'user_id': 'user-1',
        'reservation_id': reservation_id,
        'idempotency_key': 'client:key',
        'request_fingerprint': 'a' * 64,
        'owner_token_hash': 'b' * 64,
        'amount': 1,
        'remaining': 2,
        'max_usage': 5,
    }


@pytest.mark.parametrize(
    ('field', 'bad_value'),
    [
        ('request_fingerprint', 'not-a-sha256'),
        ('owner_token_hash', True),
        ('amount', '1'),
    ],
)
def test_corrupt_job_fails_closed_without_rewriting_ledger(field, bad_value):
    """손상 필드는 raw KeyError가 아니라 회계 503으로 수렴하고 원본을 보존."""
    with tempfile.TemporaryDirectory() as directory:
        queue_path = Path(directory) / 'refunds.json'
        job = _refund_job()
        job[field] = bad_value
        raw = ('{"reservation-1":' + __import__('json').dumps(job) + '}').encode()
        queue_path.write_bytes(raw)

        with (
            patch.dict(os.environ, {'USAGE_REFUND_QUEUE_PATH': str(queue_path)}),
            patch('services.usage.usage_service.mark_usage_accounting_unavailable'),
            patch(
                'src.contexts.identity.infrastructure.supabase_usage_gateway.'
                'SupabaseUsageGateway.refund',
            ) as refund,
        ):
            with pytest.raises(UsageAccountingUnavailable):
                UsageService.reconcile_pending_refunds('user-1')

        refund.assert_not_called()
        assert queue_path.read_bytes() == raw


def test_missing_job_field_fails_closed_instead_of_raw_key_error():
    with tempfile.TemporaryDirectory() as directory:
        queue_path = Path(directory) / 'refunds.json'
        job = _refund_job()
        del job['owner_token_hash']
        raw = ('{"reservation-1":' + __import__('json').dumps(job) + '}').encode()
        queue_path.write_bytes(raw)

        with (
            patch.dict(os.environ, {'USAGE_REFUND_QUEUE_PATH': str(queue_path)}),
            patch('services.usage.usage_service.mark_usage_accounting_unavailable'),
        ):
            with pytest.raises(UsageAccountingUnavailable) as exc_info:
                UsageService.reconcile_pending_refunds('user-1')

        assert not isinstance(exc_info.value.__cause__, KeyError)
        assert queue_path.read_bytes() == raw


def test_missing_stored_metadata_fails_closed_before_sorting():
    with tempfile.TemporaryDirectory() as directory:
        queue_path = Path(directory) / 'refunds.json'
        job = _refund_job()
        raw = ('{"reservation-1":' + __import__('json').dumps(job) + '}').encode()
        queue_path.write_bytes(raw)

        with (
            patch.dict(os.environ, {'USAGE_REFUND_QUEUE_PATH': str(queue_path)}),
            patch('services.usage.usage_service.mark_usage_accounting_unavailable'),
        ):
            with pytest.raises(UsageAccountingUnavailable) as exc_info:
                UsageService.reconcile_pending_refunds('user-1')

        assert not isinstance(exc_info.value.__cause__, KeyError)
        assert queue_path.read_bytes() == raw


def test_bounded_queue_rejects_new_job_without_evicting_unresolved_job():
    """용량 한도는 기존 미환불 작업을 삭제하지 않고 새 기록을 거부한다."""
    with tempfile.TemporaryDirectory() as directory:
        queue_path = Path(directory) / 'refunds.json'
        with (
            patch.dict(os.environ, {'USAGE_REFUND_QUEUE_PATH': str(queue_path)}),
            patch('services.usage.refund_queue._MAX_JOBS', 1),
        ):
            enqueue_refund(_refund_job('reservation-1'), 'first failure')
            original = queue_path.read_bytes()
            with pytest.raises(RefundQueueCapacityExceeded):
                enqueue_refund(_refund_job('reservation-2'), 'second failure')

            assert queue_path.read_bytes() == original
            assert pending_refund_count('user-1') == 1


def test_oversized_ledger_fails_before_json_parse_and_is_not_rewritten():
    with tempfile.TemporaryDirectory() as directory:
        queue_path = Path(directory) / 'refunds.json'
        raw = b'{' + b'x' * 256 + b'}'
        queue_path.write_bytes(raw)
        with (
            patch.dict(os.environ, {'USAGE_REFUND_QUEUE_PATH': str(queue_path)}),
            patch('services.usage.refund_queue._MAX_QUEUE_BYTES', 128),
        ):
            with pytest.raises(RefundQueueCapacityExceeded):
                pending_refunds_for_user('user-1')
        assert queue_path.read_bytes() == raw


def test_ambiguous_reservation_is_persisted_then_not_found_is_safe_noop():
    """예약·보상 응답이 모두 유실돼도 다음 같은 사용자가 안전하게 수렴."""
    from flask import Flask
    from src.contexts.identity.infrastructure.supabase_account_repository import (
        SupabaseAccountRepository,
    )

    app = Flask(__name__)
    client = MagicMock()
    client.rpc.return_value.execute.side_effect = [
        ConnectionError('reserve response 1 lost'),
        ConnectionError('reserve response 2 lost'),
        ConnectionError('compensation response 1 lost'),
        ConnectionError('compensation response 2 lost'),
    ]
    repository = SupabaseAccountRepository()
    repository._get_usage_rpc_client = MagicMock(return_value=client)

    with tempfile.TemporaryDirectory() as directory:
        queue_path = Path(directory) / 'refunds.json'
        with (
            app.test_request_context('/generate', method='POST'),
            patch.dict(os.environ, {'USAGE_REFUND_QUEUE_PATH': str(queue_path)}),
            patch('services.usage.usage_service.is_supabase_enabled', return_value=True),
            patch('services.usage.usage_service._is_admin_cached', return_value=False),
            patch(
                'services.usage.usage_service.UsageService.request_identity',
                return_value=('client:key', 'a' * 64),
            ),
            patch(
                'services.usage.usage_service._get_account_repository',
                return_value=repository,
            ),
            patch('services.usage.usage_service.mark_usage_accounting_unavailable'),
        ):
            with pytest.raises(UsageAccountingUnavailable):
                UsageService.reserve_for_request('user-1')

            jobs = pending_refunds_for_user('user-1')
            assert len(jobs) == 1
            assert jobs[0]['reservation_id'].startswith('ambiguous:')
            first_reserve_params = client.rpc.call_args_list[0].args[1]
            assert (
                jobs[0]['owner_token_hash']
                == first_reserve_params['p_owner_token_hash']
            )

            response = MagicMock()
            response.data = {
                'success': False,
                'reason': 'reservation_not_found',
            }
            client.rpc.return_value.execute.side_effect = None
            client.rpc.return_value.execute.return_value = response

            assert UsageService.reconcile_pending_refunds('user-1') == 1
            assert pending_refund_count('user-1') == 0
