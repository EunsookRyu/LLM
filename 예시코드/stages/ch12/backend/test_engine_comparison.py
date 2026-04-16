# test_engine_comparison.py
# 가이드 참조: chapter12_multi_engine.md L729–L824
"""
두 엔진의 응답 품질을 비교하는 테스트 스크립트.
"""

import asyncio
import json
from datetime import datetime

from services.llm import llm_service
from services.embeddings import embedding_service
from services.vector_store import vector_store
from config import config


TEST_QUERIES = [
    "연차 휴가 신청 절차가 어떻게 되나요?",
    "출장비 정산 방법을 알려주세요.",
    "재택근무 신청 방법을 알려주세요.",
    "사내 카페에서 외부 음식을 먹을 수 있나요?",       # 할루시네이션 테스트
]


async def run_test():
    print(f"테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"LLM 엔진: {config.LLM_PROVIDER}")
    print(f"임베딩 엔진: {config.EMBEDDING_PROVIDER}")
    print("=" * 60)

    results = []

    for query in TEST_QUERIES:
        print(f"\n질문: {query}")

        query_embedding = await embedding_service.embed(query)
        search_results = vector_store.search(query_embedding, top_k=3)

        context_parts = []
        for r in search_results:
            source = r.get("source", "")
            text = r["text"]
            context_parts.append(f"출처: {source}\n내용: {text}")
        context = "\n\n".join(context_parts)

        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 조직의 내부 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다. "
                    "주어진 참고 문서를 바탕으로 질문에 답변하세요. "
                    "문서에 없는 내용은 모른다고 답변하세요."
                )
            },
            {
                "role": "user",
                "content": (
                    f"참고 문서:\n{context}\n\n질문: {query}"
                    if context else query
                )
            }
        ]

        start_time = asyncio.get_event_loop().time()
        answer = await llm_service.generate(messages, max_tokens=300)
        elapsed = asyncio.get_event_loop().time() - start_time

        print(f"응답 시간: {elapsed:.2f}초")
        print(f"답변: {answer[:200]}{'...' if len(answer) > 200 else ''}")

        results.append({
            "query": query,
            "answer": answer,
            "elapsed": round(elapsed, 2),
            "search_count": len(search_results),
        })

    output_file = f"test_results_{config.LLM_PROVIDER}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_file}")
    avg_time = sum(r["elapsed"] for r in results) / len(results)
    print(f"평균 응답 시간: {avg_time:.2f}초")


if __name__ == "__main__":
    asyncio.run(run_test())
