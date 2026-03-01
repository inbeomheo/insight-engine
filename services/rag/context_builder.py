"""검색 결과를 프롬프트 삽입용 컨텍스트로 변환"""


class RAGContextBuilder:
    def __init__(self, vector_store):
        self.vector_store = vector_store

    def build_context(self, user_id: str, query: str, top_k: int = 5) -> str:
        """쿼리로 관련 문서 검색 후 프롬프트 삽입용 텍스트 반환"""
        results = self.vector_store.search(user_id, query, top_k)
        if not results:
            return ""

        context_parts = []
        for i, r in enumerate(results, 1):
            source = r['metadata'].get('filename', '문서')
            context_parts.append(f"[참고자료 {i} - {source}]\n{r['text']}")

        return "\n\n".join(context_parts)
