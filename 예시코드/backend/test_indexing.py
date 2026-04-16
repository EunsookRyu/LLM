# test_indexing.py
import asyncio
from services.indexer import indexing_pipeline
from services.embeddings import embedding_service
from services.vector_store import vector_store


async def test():
    # 1. 문서 인덱싱
    print("=== 문서 인덱싱 테스트 ===")
    result = await indexing_pipeline.index_file("test_document.txt")
    print(f"결과: {result}")

    # 2. 인덱싱된 벡터 수 확인
    print("\n=== 컬렉션 정보 ===")
    info = vector_store.get_collection_info()
    print(info)

    # 3. 검색 테스트
    print("\n=== 검색 테스트 ===")
    queries = [
        "연차 휴가 신청 절차가 어떻게 되나요?",
        "출장비 정산 기한은 어떻게 되나요?",
        "재택근무 신청 방법을 알려주세요.",
    ]

    for query in queries:
        print(f"\n질문: {query}")
        query_embedding = await embedding_service.embed(query)
        results = vector_store.search(query_embedding, top_k=2)
        for i, result in enumerate(results):
            print(f"  결과 {i+1} (점수: {result['score']:.4f}): {result['text'][:80]}...")


if __name__ == "__main__":
    asyncio.run(test())
