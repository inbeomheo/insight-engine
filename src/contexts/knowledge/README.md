# Knowledge & Context BC

## 책임
RAG(Retrieval-Augmented Generation) 지식 문서를 인덱싱·검색하는 단일 권위 BC.
파일 업로드 → 청킹 → 벡터 임베딩 → 검색 → 프롬프트 컨텍스트 주입.

## 유비쿼터스 언어
- **KnowledgeDocument**: 워크스페이스에 등록된 한 지식 문서 (Aggregate Root)
- **KnowledgeChunk**: 문서를 청킹한 단편 (텍스트 + 메타데이터 + 선택적 임베딩)
- **DocumentId**: 문서 식별자
- **ChunkId**: 청크 식별자 (보통 `{doc_id}_chunk_{idx}`)
- **WorkspaceId**: 문서가 속한 워크스페이스 (Identity BC 연동)
- **SourceType**: 문서 출처 — PDF / MARKDOWN / TEXT / WEB / NOTE
- **RetrievedChunk**: 검색 결과 1건 (chunk + 거리/관련도 점수)

## Aggregate
**KnowledgeDocument** (루트) — `KnowledgeChunk[]`.

## 외부 ACL
- `IVectorStore` — 벡터 인덱싱/검색 (어댑터: ChromaDB)
- `IKnowledgeRepository` — 문서 메타 영속 (어댑터: 인메모리/Supabase)
- `ITextChunker` — 텍스트를 청크로 분할 (어댑터: 글자 슬라이딩 윈도우)
- `IEmbeddingProvider` *(선택)* — 텍스트 → 벡터 임베딩. ChromaDB 기본 임베더를 쓰면 미주입 가능.

## 유스케이스
- **IndexDocumentUseCase**: 텍스트 → 청킹 → 벡터 인덱싱 + 메타 저장
- **RetrieveContextUseCase**: 쿼리 → 벡터 검색 → 상위 K개 청크 반환
- **DeleteDocumentUseCase**: 문서 + 모든 청크 삭제 (저장소/인덱스)
- **ListDocumentsUseCase**: 워크스페이스 내 문서 목록 조회

## 의존 방향
- 다른 BC → Knowledge: `RetrieveContextUseCase`, `IndexDocumentUseCase`
- Knowledge → 다른 BC: 없음 (단방향). `WorkspaceId`는 값 객체로만 의존.

## 현재 진척 (Phase 4)
- 도메인 모델 + 포트 + UseCase 골격 완료
- 어댑터 3종: `ChromaVectorStore`(services/rag/vector_store wrap),
  `DefaultTextChunker`(services/rag/chunker wrap), `InMemoryKnowledgeRepository`
- 단위 테스트: 도메인 / UseCase / 어댑터
- ContentGeneration 흐름 마이그레이션: 다음 PR (`services/core/ai_service.py`의 `context_builder` 직결 → UseCase 호출)
- 기존 `services/rag/*` 코드 일체 수정 없음 (안전한 wrap)
