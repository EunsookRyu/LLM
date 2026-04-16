# services/retriever.py
from services.embeddings import embedding_service
from services.vector_store import vector_store


class RetrieverService:
    """
    사용자 질문에 관련된 문서를 Qdrant에서 검색하는 서비스.
    """

    def __init__(
        self,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ):
        """
        top_k: 검색 결과로 반환할 최대 문서 수
        score_threshold: 이 점수 미만의 결과는 관련성이 낮다고 판단하여 제외
        """
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.embedding_svc = embedding_service
        self.vector_svc = vector_store

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_conditions: dict | None = None,
    ) -> list[dict]:
        """
        질문과 관련된 문서를 검색하여 반환한다.

        반환값은 유사도 점수 내림차순으로 정렬된 문서 목록이다.
        score_threshold 미만의 결과는 제외된다.
        """
        k = top_k or self.top_k

        # 1. 질문을 임베딩 벡터로 변환한다.
        query_embedding = await self.embedding_svc.embed(query)

        # 2. Qdrant에서 유사한 문서를 검색한다.
        results = self.vector_svc.search(
            query_embedding=query_embedding,
            top_k=k,
            filter_conditions=filter_conditions,
        )

        # 3. 유사도 점수가 임계값 미만인 결과를 제거한다.
        filtered = [r for r in results if r["score"] >= self.score_threshold]

        return filtered

    async def retrieve_with_dedup(
        self,
        query: str,
        top_k: int | None = None,
        filter_conditions: dict | None = None,
    ) -> list[dict]:
        """
        검색 후 중복 내용이 있는 문서를 제거하여 반환한다.
        오버랩 청킹으로 인해 유사한 내용의 청크가 중복 검색되는 경우를 처리한다.
        """
        # 중복 제거를 고려하여 요청 수보다 여유 있게 검색한다.
        k = top_k or self.top_k
        raw_results = await self.retrieve(
            query=query,
            top_k=k * 2,
            filter_conditions=filter_conditions,
        )

        # 텍스트 내용이 80% 이상 겹치는 결과를 중복으로 판단하여 제거한다.
        unique_results = []
        seen_texts = []

        for result in raw_results:
            text = result["text"]
            is_duplicate = False

            for seen in seen_texts:
                if self._similarity_ratio(text, seen) > 0.8:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_results.append(result)
                seen_texts.append(text)

            if len(unique_results) >= k:
                break

        return unique_results

    def _similarity_ratio(self, text1: str, text2: str) -> float:
        """
        두 텍스트의 단순 문자 겹침 비율을 계산한다.
        정확한 유사도 계산보다 빠른 처리가 목적이다.
        """
        if not text1 or not text2:
            return 0.0

        shorter = text1 if len(text1) <= len(text2) else text2
        longer = text2 if len(text1) <= len(text2) else text1

        if not longer:
            return 0.0

        matches = sum(1 for char in shorter if char in longer)
        return matches / len(longer)

    def format_context(self, results: list[dict]) -> str:
        """
        검색된 문서 목록을 LLM 프롬프트에 포함할 형식으로 변환한다.
        """
        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results):
            source = result.get("source", "알 수 없는 출처")
            page = result.get("page", "")
            text = result["text"]

            page_info = f" ({page}페이지)" if page else ""
            header = f"--- 참고 문서 {i + 1} | 출처: {source}{page_info} ---"
            context_parts.append(f"{header}\n{text}")

        return "\n\n".join(context_parts)


# 싱글톤 인스턴스
retriever = RetrieverService(top_k=5, score_threshold=0.5)
