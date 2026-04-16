# services/embeddings.py
# 가이드 참조: chapter7_qdrant.md L293–L367
# Ch07 시점: HyperCLOVA X 전용 (Ch12에서 멀티엔진으로 확장됨)
import httpx
from config import config


class HyperClovaXEmbeddingService:
    """
    HyperCLOVA X 임베딩 API를 호출하는 서비스 클래스.

    나중에 로컬 임베딩 서버(BGE-M3)로 교체할 때 이 클래스를 대체한다.
    외부에서는 embed()와 embed_batch() 메서드만 사용하므로,
    교체 시 동일한 인터페이스를 유지하면 된다.
    """

    BASE_URL = "https://clovastudio.stream.ntruss.com/testapp/v1/api-tools"
    MODEL = "clir-sts-dolphin"
    VECTOR_SIZE = 1024  # 이 모델이 생성하는 벡터의 차원 수

    def __init__(self):
        self.headers = {
            "X-NCP-CLOVASTUDIO-API-KEY": config.CLOVA_API_KEY,
            "X-NCP-APIGW-API-KEY": config.CLOVA_API_GATEWAY_KEY,
            "Content-Type": "application/json",
        }

    async def embed(self, text: str) -> list[float]:
        """단일 텍스트를 임베딩 벡터로 변환한다."""
        url = f"{self.BASE_URL}/embedding/{self.MODEL}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers=self.headers,
                json={"text": text}
            )
            response.raise_for_status()
            data = response.json()

        return data["result"]["embedding"]

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 10
    ) -> list[list[float]]:
        """
        여러 텍스트를 배치 단위로 임베딩한다.
        API 요청 횟수를 제한하기 위해 배치 크기를 조절한다.
        """
        import asyncio

        embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            # 배치 안의 텍스트들은 병렬로 처리한다.
            batch_embeddings = await asyncio.gather(
                *[self.embed(text) for text in batch]
            )
            embeddings.extend(batch_embeddings)
            print(f"임베딩 진행: {min(i + batch_size, total)}/{total}")

            # API 요청 한도 초과를 방지하기 위해 배치 사이에 잠시 대기한다.
            if i + batch_size < total:
                await asyncio.sleep(0.5)

        return embeddings


# 싱글톤 인스턴스
# 교체 시 이 한 줄만 변경하면 된다.
embedding_service = HyperClovaXEmbeddingService()
