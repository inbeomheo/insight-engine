from unittest.mock import MagicMock, patch

from services.content import note_index_service

_OWNER_ID = "user-a"
_OWNER_SCOPE = note_index_service.owner_scope_for(_OWNER_ID)


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

    note_index_service.index_note(_note(), owner_id=_OWNER_ID)

    client.get_or_create_collection.assert_called_once_with(
        name=note_index_service.NOTES_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    collection.upsert.assert_called_once()
    kwargs = collection.upsert.call_args.kwargs
    assert kwargs["ids"] == [f"{_OWNER_SCOPE}:note-1"]
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
        "note_id": "note-1",
        "owner_scope": _OWNER_SCOPE,
    }]


@patch("services.content.note_index_service.get_chroma_client")
def test_search_notes_returns_mapped_results(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 2
    collection.query.return_value = {
        "ids": [["note-1", "note-2"]],
        "documents": [["AI 요약 A", "요약 B"]],
        "metadatas": [[
            {"title": "글 A", "note_id": "note-1", "owner_scope": _OWNER_SCOPE},
            {"title": "글 B", "note_id": "note-2", "owner_scope": _OWNER_SCOPE},
        ]],
        "distances": [[0.2, 0.8]],
    }

    results = note_index_service.search_notes("AI", owner_id=_OWNER_ID, limit=5)

    collection.query.assert_called_once_with(
        query_texts=["AI"],
        n_results=2,
        where={"owner_scope": _OWNER_SCOPE},
    )
    assert results == [
        {"id": "note-1", "title": "글 A", "score": 0.8, "snippet": "AI 요약 A", "highlight_ranges": [[0, 2]]},
        {"id": "note-2", "title": "글 B", "score": 0.2, "snippet": "요약 B", "highlight_ranges": []},
    ]


@patch("services.content.note_index_service.get_chroma_client")
def test_search_notes_empty_collection_returns_empty_list(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 0

    assert note_index_service.search_notes("AI", owner_id=_OWNER_ID) == []
    collection.query.assert_not_called()


@patch("services.content.note_index_service.get_chroma_client")
def test_get_related_notes_excludes_self_and_limits(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 4
    collection.query.return_value = {
        "ids": [["note-1", "note-2", "note-3"]],
        "documents": [["요약 self", "요약 B", "요약 C"]],
        "metadatas": [[
            {"title": "현재 글", "note_id": "note-1", "owner_scope": _OWNER_SCOPE},
            {"title": "관련 글 B", "note_id": "note-2", "owner_scope": _OWNER_SCOPE},
            {"title": "관련 글 C", "note_id": "note-3", "owner_scope": _OWNER_SCOPE},
        ]],
        "distances": [[0.0, 0.1, 0.3]],
    }

    results = note_index_service.get_related_notes(_note(), owner_id=_OWNER_ID, limit=2)

    collection.query.assert_called_once_with(query_texts=[
        "핵심 개념: 개념 A, 개념 B\n요약: 핵심 요약입니다.\n학습 포인트: 핵심 요약을 실무에 적용한다.\n복습 질문: 무엇을 적용하나? 핵심 요약입니다.\n근거 인용: 근거 문장 p1\n태그: AI, 학습"
    ], n_results=3, where={"owner_scope": _OWNER_SCOPE})
    assert [item["id"] for item in results] == ["note-2", "note-3"]
    assert results[0]["title"] == "관련 글 B"
    assert all(item["highlight_ranges"] == [] for item in results)


@patch("services.content.note_index_service.get_chroma_client")
def test_get_related_notes_searches_single_other_note_when_self_missing(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 1
    collection.query.return_value = {
        "ids": [["note-2"]],
        "documents": [["요약 B"]],
        "metadatas": [[{
            "title": "관련 글 B",
            "note_id": "note-2",
            "owner_scope": _OWNER_SCOPE,
        }]],
        "distances": [[0.1]],
    }

    results = note_index_service.get_related_notes(_note(), owner_id=_OWNER_ID, limit=3)

    collection.query.assert_called_once_with(query_texts=[
        "핵심 개념: 개념 A, 개념 B\n요약: 핵심 요약입니다.\n학습 포인트: 핵심 요약을 실무에 적용한다.\n복습 질문: 무엇을 적용하나? 핵심 요약입니다.\n근거 인용: 근거 문장 p1\n태그: AI, 학습"
    ], n_results=1, where={"owner_scope": _OWNER_SCOPE})
    assert [item["id"] for item in results] == ["note-2"]


@patch("services.content.note_index_service.get_chroma_client")
def test_get_related_notes_uses_related_default_and_caps_query_limit(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 30
    collection.query.return_value = {
        "ids": [[f"note-{idx}" for idx in range(1, 21)]],
        "documents": [["요약"] * 20],
        "metadatas": [[{
            "note_id": f"note-{idx}",
            "owner_scope": _OWNER_SCOPE,
        } for idx in range(1, 21)]],
        "distances": [[0.1] * 20],
    }

    note_index_service.get_related_notes(_note(), owner_id=_OWNER_ID, limit=None)
    collection.query.assert_called_once_with(query_texts=[
        "핵심 개념: 개념 A, 개념 B\n요약: 핵심 요약입니다.\n학습 포인트: 핵심 요약을 실무에 적용한다.\n복습 질문: 무엇을 적용하나? 핵심 요약입니다.\n근거 인용: 근거 문장 p1\n태그: AI, 학습"
    ], n_results=4, where={"owner_scope": _OWNER_SCOPE})

    collection.query.reset_mock()
    capped_results = note_index_service.get_related_notes(
        _note(),
        owner_id=_OWNER_ID,
        limit=20,
    )
    collection.query.assert_called_once_with(query_texts=[
        "핵심 개념: 개념 A, 개념 B\n요약: 핵심 요약입니다.\n학습 포인트: 핵심 요약을 실무에 적용한다.\n복습 질문: 무엇을 적용하나? 핵심 요약입니다.\n근거 인용: 근거 문장 p1\n태그: AI, 학습"
    ], n_results=20, where={"owner_scope": _OWNER_SCOPE})
    assert len(capped_results) == 19


@patch("services.content.note_index_service.get_chroma_client")
def test_remove_note_deletes_id(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)

    note_index_service.remove_note("note-1", owner_id=_OWNER_ID)

    collection.delete.assert_called_once_with(ids=[f"{_OWNER_SCOPE}:note-1"])


def test_snippet_centers_late_exact_phrase_with_prefix_ellipsis():
    text = "intro " + ("early context " * 30) + "target exact phrase" + (" trailing" * 20)
    query = "target   exact" + chr(10) + "phrase"

    snippet = note_index_service._snippet(text, query)

    assert "target exact phrase" in snippet
    assert snippet.startswith(chr(0x2026))
    assert len(snippet) <= note_index_service.SNIPPET_MAX_CHARS


def test_snippet_falls_back_to_longest_distinct_query_token():
    text = "common " + ("early words " * 30) + "specificlongtoken nearby evidence" + (" tail" * 20)

    snippet = note_index_service._snippet(text, "common missing specificlongtoken common")

    assert "specificlongtoken" in snippet
    assert "common" not in snippet


def test_snippet_matches_exact_phrase_case_insensitively():
    text = ("prefix " * 30) + "Adaptive REVIEW context" + (" suffix" * 20)

    snippet = note_index_service._snippet(text, "adaptive review")

    assert "Adaptive REVIEW" in snippet


def test_snippet_matches_unicode_word_token():
    term = "".join(chr(value) for value in (0xAC80, 0xC0C9, 0xC5B4))
    evidence = "".join(chr(value) for value in (0xADFC, 0xAC70))
    text = ("prefix " * 30) + term + " " + evidence + (" suffix" * 20)

    snippet = note_index_service._snippet(text, term)

    assert term + " " + evidence in snippet


def test_snippet_uses_leading_fallback_for_missing_empty_and_numeric_queries():
    text = "leading evidence " + ("content " * 60) + "late target"
    expected = note_index_service._snippet(text)

    assert note_index_service._snippet(text, "not present") == expected
    assert note_index_service._snippet(text, "  " + chr(10) + chr(9) + " ") == expected
    assert note_index_service._snippet(text, "123 !!!") == expected


def test_leading_fallback_preserves_boundary_space_exactly():
    text = ("A" * 178) + " " + "tail"

    assert note_index_service._snippet(text, "missing") == ("A" * 178) + " " + chr(0x2026)


def test_query_candidates_keep_casefold_expansions_when_regex_rules_differ():
    sharp_s = chr(0x00DF)
    text = ("prefix " * 30) + sharp_s + " evidence" + (" suffix" * 20)

    snippet = note_index_service._snippet(text, sharp_s + " ss")

    assert sharp_s + " evidence" in snippet
    assert sharp_s in note_index_service._query_candidates(sharp_s + " ss")
    assert "ss" in note_index_service._query_candidates(sharp_s + " ss")


def test_long_query_tokens_still_select_matching_context():
    for length in (178, 179, 180):
        token = "z" * length
        text = ("leading context " * 30) + token + (" trailing context" * 30)

        snippet = note_index_service._snippet(text, token)

        assert ("z" * 50) in snippet
        assert "leading context" not in snippet
        assert snippet.startswith(chr(0x2026))
        assert snippet.endswith(chr(0x2026))
        assert len(snippet) <= note_index_service.SNIPPET_MAX_CHARS


def test_179_character_token_is_preserved_at_start_and_end():
    token = "z" * 179
    start_snippet = note_index_service._snippet(token + (" tail" * 20), token)
    end_snippet = note_index_service._snippet(("prefix " * 20) + token, token)

    assert start_snippet.startswith(token)
    assert start_snippet.endswith(chr(0x2026))
    assert end_snippet.startswith(chr(0x2026))
    assert end_snippet.endswith(token)
    assert len(start_snippet) == note_index_service.SNIPPET_MAX_CHARS
    assert len(end_snippet) == note_index_service.SNIPPET_MAX_CHARS


def test_snippet_marks_both_cut_edges_and_stays_within_limit():
    text = ("left context " * 40) + "needle" + (" right context" * 40)

    snippet = note_index_service._snippet(text, "needle")

    assert snippet.startswith(chr(0x2026))
    assert snippet.endswith(chr(0x2026))
    assert "needle" in snippet
    assert len(snippet) <= note_index_service.SNIPPET_MAX_CHARS


def test_snippet_marks_only_the_cut_edge_at_document_boundaries():
    front = "frontmatch " + ("right context " * 50)
    end = ("left context " * 50) + "endmatch"

    front_snippet = note_index_service._snippet(front, "frontmatch")
    end_snippet = note_index_service._snippet(end, "endmatch")

    assert front_snippet.startswith("frontmatch")
    assert front_snippet.endswith(chr(0x2026))
    assert end_snippet.startswith(chr(0x2026))
    assert end_snippet.endswith("endmatch")
    assert len(front_snippet) <= note_index_service.SNIPPET_MAX_CHARS
    assert len(end_snippet) <= note_index_service.SNIPPET_MAX_CHARS


def test_snippet_returns_normalized_short_document_unchanged():
    text = "  short" + chr(10) + chr(9) + "text  "
    assert note_index_service._snippet(text, "short") == "short text"


def test_snippet_highlight_ranges_follow_python_phrase_token_and_case_matching():
    cases = [
        ("prefix Adaptive REVIEW suffix", "adaptive review", "Adaptive REVIEW"),
        ("prefix specificlongtoken suffix", "missing specificlongtoken", "specificlongtoken"),
        ("앞 İ 뒤", "i", "İ"),
    ]

    for text, query, expected in cases:
        snippet, ranges = note_index_service._snippet_with_highlights(text, query)

        assert len(ranges) == 1
        start, end = ranges[0]
        assert snippet[start:end] == expected
        assert 0 <= start < end <= len(snippet)


def test_snippet_highlight_ranges_are_empty_for_missing_numeric_and_related_queries():
    text = "leading 2026 evidence"

    assert note_index_service._snippet_with_highlights(text, "missing")[1] == []
    assert note_index_service._snippet_with_highlights(text, "2026 !!!")[1] == []
    assert note_index_service._snippet_with_highlights(text)[1] == []


def test_long_match_highlight_range_only_covers_visible_body_and_excludes_ellipses():
    for length in (179, 180):
        token = "z" * length
        text = ("leading context " * 30) + token + (" trailing context" * 30)

        snippet, ranges = note_index_service._snippet_with_highlights(text, token)

        assert len(snippet) == note_index_service.SNIPPET_MAX_CHARS
        assert snippet.startswith(chr(0x2026))
        assert snippet.endswith(chr(0x2026))
        assert ranges == [[1, note_index_service.SNIPPET_MAX_CHARS - 1]]
        start, end = ranges[0]
        assert snippet[start:end] == token[:end - start]


def test_boundary_long_match_range_excludes_single_ellipsis():
    token = "z" * 179

    start_snippet, start_ranges = note_index_service._snippet_with_highlights(
        token + (" tail" * 20),
        token,
    )
    end_snippet, end_ranges = note_index_service._snippet_with_highlights(
        ("prefix " * 20) + token,
        token,
    )

    assert start_ranges == [[0, 179]]
    assert start_snippet[0:179] == token
    assert start_snippet[179:] == chr(0x2026)
    assert end_ranges == [[1, 180]]
    assert end_snippet[0] == chr(0x2026)
    assert end_snippet[1:180] == token


@patch("services.content.note_index_service._map_results")
@patch("services.content.note_index_service.get_chroma_client")
def test_search_notes_passes_normalized_query_to_result_mapping(mock_get_client, mock_map_results):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 1
    collection.query.return_value = {"documents": [["document"]]}
    mock_map_results.return_value = []
    query = "  target" + chr(10) + " phrase  "

    note_index_service.search_notes(query, owner_id=_OWNER_ID)

    collection.query.assert_called_once_with(
        query_texts=["target phrase"],
        n_results=1,
        where={"owner_scope": _OWNER_SCOPE},
    )
    mock_map_results.assert_called_once_with(
        collection.query.return_value,
        query="target phrase",
        expected_owner_scope=_OWNER_SCOPE,
    )


@patch("services.content.note_index_service._map_results")
@patch("services.content.note_index_service.get_chroma_client")
def test_get_related_notes_keeps_leading_snippet_mapping(mock_get_client, mock_map_results):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 1
    collection.query.return_value = {"documents": [["document"]]}
    mock_map_results.return_value = []

    note_index_service.get_related_notes(_note(), owner_id=_OWNER_ID)

    mock_map_results.assert_called_once_with(
        collection.query.return_value,
        expected_owner_scope=_OWNER_SCOPE,
    )


@patch("services.content.note_index_service.get_chroma_client")
def test_search_notes_filters_and_rejects_cross_owner_results(mock_get_client):
    collection, _ = _mock_collection(mock_get_client)
    collection.count.return_value = 2
    collection.query.return_value = {
        "ids": [[f"{_OWNER_SCOPE}:mine", "other-scope:theirs"]],
        "documents": [["내 근거", "다른 사용자 비밀"]],
        "metadatas": [[
            {"title": "내 노트", "note_id": "mine", "owner_scope": _OWNER_SCOPE},
            {"title": "타인 노트", "note_id": "theirs", "owner_scope": "other-scope"},
        ]],
        "distances": [[0.1, 0.1]],
    }

    results = note_index_service.search_notes("근거", owner_id=_OWNER_ID)

    assert [item["id"] for item in results] == ["mine"]
    assert all("비밀" not in item["snippet"] for item in results)
    collection.query.assert_called_once_with(
        query_texts=["근거"],
        n_results=2,
        where={"owner_scope": _OWNER_SCOPE},
    )


def test_map_results_uses_query_context_for_search_snippet():
    document = ("prefix " * 30) + "matching phrase context" + (" suffix" * 20)

    mapped = note_index_service._map_results(
        {
            "ids": [["note-1"]],
            "documents": [[document]],
            "metadatas": [[{"title": "Title"}]],
            "distances": [[0.2]],
        },
        query="matching phrase",
    )

    assert "matching phrase" in mapped[0]["snippet"]
    assert mapped[0]["snippet"].startswith(chr(0x2026))
    assert len(mapped[0]["highlight_ranges"]) == 1
    start, end = mapped[0]["highlight_ranges"][0]
    assert mapped[0]["snippet"][start:end] == "matching phrase"


def test_map_results_tolerates_malformed_shapes_and_missing_values():
    assert note_index_service._map_results(None) == []
    assert note_index_service._map_results({"documents": "not a list"}) == []

    document = "  short" + chr(10) + "text  "
    mapped = note_index_service._map_results({
        "ids": [[None]],
        "documents": [[document]],
        "metadatas": [["not metadata"]],
        "distances": [["not distance"]],
    })

    assert mapped == [{
        "id": "None",
        "title": "",
        "score": 0.0,
        "snippet": "short text",
        "highlight_ranges": [],
    }]


def test_map_results_clamps_and_rounds_scores():
    mapped = note_index_service._map_results({
        "ids": [["high", "low", "rounded"]],
        "documents": [["A", "B", "C"]],
        "metadatas": [[{}, {}, {}]],
        "distances": [[-0.5, 2, 0.1236]],
    })

    assert [item["score"] for item in mapped] == [1.0, 0.0, 0.876]
