"""ChromaDB 기반 벡터 저장소"""
import os
import logging

from services.rag.chroma_client_factory import get_chroma_client
from utils.runtime_paths import app_data_path

logger = logging.getLogger(__name__)


class VectorStore:
    def __init__(self, db_path: str | None = None):
        db_path = db_path or os.environ.get('CHROMA_DB_PATH') or app_data_path('chroma_db')
        os.makedirs(db_path, exist_ok=True)
        # 프로세스 단위 싱글톤 클라이언트 사용 — video_qa_service와 동일 디렉토리 충돌 방지
        self._client = get_chroma_client(db_path)

    def _get_collection(self, user_id: str):
        """사용자별 컬렉션 반환 (없으면 생성)"""
        return self._client.get_or_create_collection(name=f"user_{user_id}")

    def add_document(self, user_id: str, doc_id: str, chunks: list, metadata: dict) -> None:
        """문서 청크를 벡터 DB에 추가"""
        collection = self._get_collection(user_id)
        ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{**metadata, "chunk_index": i, "doc_id": doc_id} for i in range(len(chunks))]
        collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        logger.info(f"문서 추가 완료: user={user_id}, doc={doc_id}, chunks={len(chunks)}")

    def search(self, user_id: str, query: str, top_k: int = 5) -> list:
        """쿼리로 관련 청크 검색"""
        collection = self._get_collection(user_id)
        if collection.count() == 0:
            return []
        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count())
        )
        return [
            {"text": doc, "metadata": meta, "distance": dist}
            for doc, meta, dist in zip(
                results['documents'][0],
                results['metadatas'][0],
                results['distances'][0]
            )
        ]

    def delete_document(self, user_id: str, doc_id: str) -> None:
        """문서의 모든 청크 삭제"""
        collection = self._get_collection(user_id)
        all_ids = collection.get()['ids']
        to_delete = [id for id in all_ids if id.startswith(f"{doc_id}_chunk_")]
        if to_delete:
            collection.delete(ids=to_delete)
            logger.info(f"문서 삭제 완료: user={user_id}, doc={doc_id}, chunks={len(to_delete)}")

    def list_documents(self, user_id: str) -> list:
        """사용자 문서 목록 (청크가 아닌 문서 단위)"""
        collection = self._get_collection(user_id)
        all_data = collection.get(include=['metadatas'])
        docs = {}
        for meta in all_data['metadatas']:
            doc_id = meta.get('doc_id')
            if doc_id and doc_id not in docs:
                docs[doc_id] = {
                    "id": doc_id,
                    "filename": meta.get('filename', ''),
                    "uploaded_at": meta.get('uploaded_at', ''),
                    "chunk_count": 0,
                }
            if doc_id:
                docs[doc_id]['chunk_count'] += 1
        return list(docs.values())


# 싱글턴 인스턴스
_db_path = os.environ.get('CHROMA_DB_PATH') or app_data_path('chroma_db')
vector_store = VectorStore(db_path=_db_path)
