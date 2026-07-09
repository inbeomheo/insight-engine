from unittest.mock import MagicMock, patch

from services.content import note_index_service


def _note():
    return {
        "id": "note-1",
        "source": {"type": "article", "url": "https://example.com/a", "title": "테스트 글"},
        "key_concepts": ["개념 A", "개념 B"],
        "summary": "핵심 요약입니다.",
        "learning_points": ["핵심 요약을 실무에 적용한다."],
        "review_questions": [{"question": "무엇을 적용하나?", "answer": "핵심 요약입니다."}],
        "quotes": [{"text": "근거 문장", "ref": "p1"}],
        "tags": ["AI", "학습"],
        "language": "ko",
        "created_at": "2026-07-04T12:00:00Z",
    }


def _mock_collection(mock_get_client):
    collection = MagicMock()
    client = MagicMock()
    client.get_or_create_collection.return_value = collection
    mock_get_client.return_value = client
    return collection, client


@patch("services.content.note_index_service.get_chroma_client")
def test_index_note_upserts_searchable_text_and_metadata(mock_get_client):
    collection, client = _mock_collection(mock_get_client)

    note_index_service.index_note(_note())

    client.get_or_create_collection.assert_called_once_with(
        name=note_index_service.NOTES_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    collection.upsert.assert_called_once()
    kwargs = collection.upsert.call_args.kwargs
    assert kwargs["ids"] == ["note-1"]
    assert "개념 A" in kwargs["documents"][0]
    assert "핵심 요약입니다." in kwargs["documents"][0]
    assert "학습 포인트" in kwargs["documents"][0]
    assert "복습 질문" in kwargs["documents"][0]
    assert "근거 문장" in kwargs["documents"][0]
    assert "AI" in kwargs["documents"][0]
    assert kwargs["metadatas"] == [{
        "title": "테스트 글",
        "source_url": "https://example.com/a",
        "created_at": "2026-07-04T12:00:00Z",
    }]


@patch("services.content.note_index_service.get_chroma_client")
def test_search_notes_returns_mapped_results(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 2
    collection.query.return_value = {
        "ids": [["note-1", "note-2"]],
        "documents": [["요약 A", "요약 B"]],
        "metadatas": [[{"title": "글 A"}, {"title": "글 B"}]],
        "distances": [[0.2, 0.8]],
    }

    results = note_index_service.search_notes("AI", limit=5)

    collection.query.assert_called_once_with(query_texts=["AI"], n_results=2)
    assert results == [
        {"id": "note-1", "title": "글 A", "score": 0.8, "snippet": "요약 A"},
        {"id": "note-2", "title": "글 B", "score": 0.2, "snippet": "요약 B"},
    ]


@patch("services.content.note_index_service.get_chroma_client")
def test_search_notes_empty_collection_returns_empty_list(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 0

    assert note_index_service.search_notes("AI") == []
    collection.query.assert_not_called()


@patch("services.content.note_index_service.get_chroma_client")
def test_get_related_notes_excludes_self_and_limits(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 4
    collection.query.return_value = {
        "ids": [["note-1", "note-2", "note-3"]],
        "documents": [["요약 self", "요약 B", "요약 C"]],
        "metadatas": [[
            {"title": "현재 글"},
            {"title": "관련 글 B"},
            {"title": "관련 글 C"},
        ]],
        "distances": [[0.0, 0.1, 0.3]],
    }

    results = note_index_service.get_related_notes(_note(), limit=2)

    collection.query.assert_called_once_with(query_texts=[
        "핵심 개념: 개념 A, 개념 B\n요약: 핵심 요약입니다.\n학습 포인트: 핵심 요약을 실무에 적용한다.\n복습 질문: 무엇을 적용하나? 핵심 요약입니다.\n근거 인용: 근거 문장 p1\n태그: AI, 학습"
    ], n_results=3)
    assert [item["id"] for item in results] == ["note-2", "note-3"]
    assert results[0]["title"] == "관련 글 B"


@patch("services.content.note_index_service.get_chroma_client")
def test_get_related_notes_searches_single_other_note_when_self_missing(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 1
    collection.query.return_value = {
        "ids": [["note-2"]],
        "documents": [["요약 B"]],
        "metadatas": [[{"title": "관련 글 B"}]],
        "distances": [[0.1]],
    }

    results = note_index_service.get_related_notes(_note(), limit=3)

    collection.query.assert_called_once_with(query_texts=[
        "핵심 개념: 개념 A, 개념 B\n요약: 핵심 요약입니다.\n학습 포인트: 핵심 요약을 실무에 적용한다.\n복습 질문: 무엇을 적용하나? 핵심 요약입니다.\n근거 인용: 근거 문장 p1\n태그: AI, 학습"
    ], n_results=1)
    assert [item["id"] for item in results] == ["note-2"]


@patch("services.content.note_index_service.get_chroma_client")
def test_get_related_notes_uses_related_default_and_caps_query_limit(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 30
    collection.query.return_value = {
        "ids": [[f"note-{idx}" for idx in range(1, 21)]],
        "documents": [["요약"] * 20],
        "metadatas": [[{}] * 20],
        "distances": [[0.1] * 20],
    }

    note_index_service.get_related_notes(_note(), limit=None)
    collection.query.assert_called_once_with(query_texts=[
        "핵심 개념: 개념 A, 개념 B\n요약: 핵심 요약입니다.\n학습 포인트: 핵심 요약을 실무에 적용한다.\n복습 질문: 무엇을 적용하나? 핵심 요약입니다.\n근거 인용: 근거 문장 p1\n태그: AI, 학습"
    ], n_results=4)

    collection.query.reset_mock()
    capped_results = note_index_service.get_related_notes(_note(), limit=20)
    collection.query.assert_called_once_with(query_texts=[
        "핵심 개념: 개념 A, 개념 B\n요약: 핵심 요약입니다.\n학습 포인트: 핵심 요약을 실무에 적용한다.\n복습 질문: 무엇을 적용하나? 핵심 요약입니다.\n근거 인용: 근거 문장 p1\n태그: AI, 학습"
    ], n_results=20)
    assert len(capped_results) == 19


@patch("services.content.note_index_service.get_chroma_client")
def test_remove_note_deletes_id(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)

    note_index_service.remove_note("note-1")

    collection.delete.assert_called_once_with(ids=["note-1"])
