"""SupabaseChannelMonitorRepository.delete 결과 검증 (PR #22).

`.execute()` 결과를 무시하고 무조건 True를 반환하면, 없는 ID/타 사용자 소유
ID 삭제 시에도 성공으로 응답되어 라우트의 404 분기가 무력화된다.
삭제된 행(result.data) 유무로 bool을 반환해야 한다.
"""
from unittest.mock import MagicMock, patch

from src.contexts.channel_monitoring.infrastructure.supabase_channel_repository import (
    SupabaseChannelMonitorRepository,
)

_GET_SUPABASE = (
    "src.contexts.channel_monitoring.infrastructure."
    "supabase_channel_repository.get_supabase"
)


def _client_returning(rows):
    client = MagicMock()
    chain = (
        client.table.return_value.delete.return_value.eq.return_value.eq.return_value
    )
    chain.execute.return_value = MagicMock(data=rows)
    return client


@patch(_GET_SUPABASE)
def test_delete_false_when_no_rows_deleted(mock_get):
    mock_get.return_value = _client_returning([])
    assert SupabaseChannelMonitorRepository().delete("u1", "m1") is False


@patch(_GET_SUPABASE)
def test_delete_true_when_row_deleted(mock_get):
    mock_get.return_value = _client_returning([{"id": "m1"}])
    assert SupabaseChannelMonitorRepository().delete("u1", "m1") is True


@patch(_GET_SUPABASE, return_value=None)
def test_delete_false_when_no_client(mock_get):
    assert SupabaseChannelMonitorRepository().delete("u1", "m1") is False
