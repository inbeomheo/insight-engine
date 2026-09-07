"""실제 임시 Chroma 저장소에서 노트 검색부터 그래프까지 검증한다."""

import pytest
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from services.content import note_graph_service, note_index_service, note_service
from services.rag import chroma_client_factory


class _TopicEmbedding(EmbeddingFunction[Documents]):
    """외부 다운로드 없이 세 주제의 출현 횟수를 벡터로 변환한다."""

    def __init__(self):
        pass

    def __call__(self, input: Documents) -> Embeddings:
        return [
            [float(text.lower().count(topic)) for topic in ("astronomy", "gardening", "cooking")]
            for text in input
        ]

    @staticmethod
    def name() -> str:
        return "native-note-test-topics"

    def get_config(self) -> dict:
        return {}

    @staticmethod
    def build_from_config(config: dict) -> "_TopicEmbedding":
        return _TopicEmbedding()


def _note(owner: str, note_id: str, topic: str) -> dict:
    return {
        "id": note_id,
        "source": {"title": f"{owner} {note_id}", "type": "text", "url": ""},
        "key_concepts": [topic],
        "summary": f"{topic}에 관한 {owner}의 학습 기록",
        "tags": [],
        "quotes": [],
        "language": "ko",
        "created_at": "2026-09-07T00:00:00+00:00",
    }


@pytest.fixture
def native_notes(tmp_path, monkeypatch):
    """저장 경로와 임베딩만 주입하며 검색·필터·파일 서비스는 실제 실행한다."""
    monkeypatch.setattr(note_service, "NOTES_DIR", tmp_path / "notes")
    monkeypatch.setattr(note_index_service, "CHROMA_DB_PATH", str(tmp_path / "chroma"))
    monkeypatch.setattr(chroma_client_factory, "_chroma_clients", {})
    client = chroma_client_factory.get_chroma_client(note_index_service.CHROMA_DB_PATH)
    get_or_create = client.get_or_create_collection
    embedding = _TopicEmbedding()

    def collection_with_local_embedding(*args, **kwargs):
        return get_or_create(*args, **kwargs, embedding_function=embedding)

    monkeypatch.setattr(client, "get_or_create_collection", collection_with_local_embedding)
    notes = {}
    for owner, topic in (("owner-a", "astronomy"), ("owner-b", "gardening")):
        notes[owner] = [
            _note(owner, "shared-target", topic),
            _note(owner, f"{owner}-related", topic),
            _note(owner, f"{owner}-unrelated", "cooking"),
        ]
        for note in notes[owner]:
            note_service.save_note(note, owner_id=owner)
            note_index_service.index_note(note, owner_id=owner)

    yield notes, note_index_service._get_collection()


@pytest.mark.parametrize("owner, topic", [("owner-a", "astronomy"), ("owner-b", "gardening")])
def test_native_search_related_graph_and_backlinks_isolate_same_note_id(native_notes, owner, topic):
    notes, collection = native_notes
    assert collection.count() == 6
    assert collection.metadata["hnsw:space"] == "cosine"

    results = note_index_service.search_notes(topic, owner_id=owner, limit=20)
    assert {result["id"] for result in results} == {note["id"] for note in notes[owner]}
    assert all(result["title"].startswith(owner) for result in results)
    assert {result["id"] for result in results if result["score"] > 0.5} == {
        "shared-target", f"{owner}-related",
    }
    for result in results[:2]:
        assert result["score"] == pytest.approx(1.0)
        start, end = result["highlight_ranges"][0]
        assert result["snippet"][start:end] == topic
    assert results[-1]["score"] == pytest.approx(0.0)

    related = note_index_service.get_related_notes(notes[owner][0], owner_id=owner, limit=19)
    assert [item["id"] for item in related] == [f"{owner}-related", f"{owner}-unrelated"]
    assert [item["score"] for item in related] == [1.0, 0.0]
    assert all(item["title"].startswith(owner) for item in related)

    # notes/related_lookup를 주입하지 않아 파일 조회와 실제 Chroma 검색을 연결한다.
    graph = note_graph_service.build_note_graph(owner_id=owner, min_score=0.5)
    assert {node["id"] for node in graph["nodes"]} == {note["id"] for note in notes[owner]}
    assert all(node["title"].startswith(owner) for node in graph["nodes"])
    assert graph["edges"] == [
        {"source": f"{owner}-related", "target": "shared-target", "score": 1.0},
        {"source": "shared-target", "target": f"{owner}-related", "score": 1.0},
    ]
    assert graph["meta"]["node_count"] == 3
    assert graph["meta"]["edge_count"] == 2
    assert note_graph_service.get_note_backlinks("shared-target", owner_id=owner, min_score=0.5) == [
        {"id": f"{owner}-related", "title": f"{owner} {owner}-related", "score": 1.0},
    ]
    other = "owner-b" if owner == "owner-a" else "owner-a"
    assert note_graph_service.get_note_backlinks(f"{other}-related", owner_id=owner) == []


def test_native_repeated_upsert_preserves_other_owner_and_refreshes_relationships(native_notes):
    _, collection = native_notes
    original_b = note_graph_service.build_note_graph(owner_id="owner-b", min_score=0.5)
    updated = _note("owner-a", "shared-target", "cooking")
    note_service.save_note(updated, owner_id="owner-a")
    note_index_service.index_note(updated, owner_id="owner-a")
    note_index_service.index_note(updated, owner_id="owner-a")

    assert collection.count() == 6
    assert note_graph_service.build_note_graph(owner_id="owner-b", min_score=0.5) == original_b
    assert note_graph_service.get_note_backlinks("shared-target", owner_id="owner-a", min_score=0.5) == [
        {"id": "owner-a-unrelated", "title": "owner-a owner-a-unrelated", "score": 1.0},
    ]
    for absent_owner in ("owner-c", None):
        assert note_index_service.search_notes("cooking", owner_id=absent_owner) == []
        assert note_graph_service.build_note_graph(owner_id=absent_owner)["nodes"] == []
        assert note_graph_service.get_note_backlinks("shared-target", owner_id=absent_owner) == []
