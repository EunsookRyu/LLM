# test_vector_store.py
import asyncio
from services.embeddings import embedding_service
from services.vector_store import vector_store


async def test():
    # 1. 샘플 텍스트 임베딩 생성
    print("=== 임베딩 생성 테스트 ===")
    texts = [
        "연차 휴가는 근속 연수에 따라 15일에서 25일까지 부여됩니다.",
        "출장비 정산은 출장 완료 후 7일 이내에 신청해야 합니다.",
        "보안 교육은 매 분기 1회 의무적으로 이수해야 합니다.",
    ]
    embeddings = await embedding_service.embed_batch(texts)
    print(f"생성된 벡터 수: {len(embeddings)}")
    print(f"벡터 차원: {len(embeddings[0])}")

    # 2. 벡터 데이터베이스에 저장
    print("\n=== 벡터 저장 테스트 ===")
    metadatas = [
        {"source": "사내_규정집_2025.pdf", "page": 8, "category": "업무규정"},
        {"source": "사내_규정집_2025.pdf", "page": 15, "category": "캠프"},
        {"source": "업무_매뉴얼.pdf", "page": 3, "category": "업무규정"},
    ]
    ids = vector_store.add_documents(texts, embeddings, metadatas)
    print(f"저장된 포인트 ID: {ids}")

    # 3. 유사도 검색
    print("\n=== 유사도 검색 테스트 ===")
    query = "출장비 정산 기한이 어떻게 되나요?"
    query_embedding = await embedding_service.embed(query)
    results = vector_store.search(query_embedding, top_k=2)

    print(f"검색 쿼리: {query}")
    for i, result in enumerate(results):
        print(f"\n결과 {i+1}:")
        print(f"  유사도 점수: {result['score']:.4f}")
        print(f"  텍스트: {result['text']}")
        print(f"  출처: {result['source']} ({result['page']}페이지)")

    # 4. 필터링 검색
    print("\n=== 필터링 검색 테스트 ===")
    filtered_results = vector_store.search(
        query_embedding,
        top_k=2,
        filter_conditions={"category": "업무규정"}
    )
    print(f"'업무규정' 카테고리에서 검색:")
    for i, result in enumerate(filtered_results):
        print(f"  결과 {i+1}: {result['text'][:40]}... (점수: {result['score']:.4f})")

    # 5. 컬렉션 정보 확인
    print("\n=== 컬렉션 정보 ===")
    info = vector_store.get_collection_info()
    print(info)


if __name__ == "__main__":
    asyncio.run(test())
