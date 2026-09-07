"""History persistence/query payloads must match the bundled Supabase schema."""
from unittest.mock import MagicMock, patch

from services.data.supabase_service import save_history
from src.contexts.content_library.domain.history_entry import HistoryEntry
from src.contexts.content_library.infrastructure.supabase_history_repository import (
    SupabaseHistoryRepository,
)


def test_single_history_insert_uses_preview_and_existing_columns_only() -> None:
    client = MagicMock()
    client.table.return_value.insert.return_value.execute.return_value.data = [
        {'id': 'row-1'},
    ]

    with patch(
        'services.data.supabase_service.get_user_supabase',
        return_value=client,
    ):
        result = save_history(
            'user-1',
            {
                'id': 'report-1',
                'transcript': 'x' * 600,
                'transcript_source': 'api',
            },
            validated_access_token='validated-token',
        )

    assert result == {'id': 'row-1'}
    payload = client.table.return_value.insert.call_args.args[0]
    assert payload['url'] == ''
    assert payload['title'] == ''
    assert payload['style'] == 'unknown'
    assert payload['transcript_preview'] == 'x' * 500
    assert 'transcript' not in payload
    assert 'transcript_source' not in payload


def test_batch_history_insert_matches_same_schema_contract() -> None:
    client = MagicMock()
    entry = HistoryEntry.from_dict(
        {
            'id': 'report-1',
            'transcript': 'y' * 600,
            'transcript_source': 'watch',
            'keywords': ['one'],
        },
        owner_id='user-1',
    )

    with patch(
        'src.contexts.content_library.infrastructure.'
        'supabase_history_repository.get_user_supabase',
        return_value=client,
    ):
        assert SupabaseHistoryRepository().save_many([entry]) == 1

    payload = client.table.return_value.insert.call_args.args[0][0]
    assert payload['transcript_preview'] == 'y' * 500
    assert payload['keywords'] == ['one']
    assert 'transcript' not in payload
    assert 'transcript_source' not in payload


def test_admin_history_query_requests_only_existing_columns() -> None:
    client = MagicMock()
    client.table.return_value.select.return_value.gte.return_value.execute.return_value.data = []

    with patch(
        'src.contexts.content_library.infrastructure.'
        'supabase_history_repository.get_service_supabase',
        return_value=client,
    ):
        assert SupabaseHistoryRepository().fetch_recent_for_admin() == []

    selected = client.table.return_value.select.call_args.args[0]
    assert selected == 'created_at,style,elapsed_time,content'
    assert 'success' not in selected
