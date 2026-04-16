# services/embeddings.py
"""
임베딩 서비스 모듈.

환경 변수 EMBEDDING_PROVIDER의 값에 따라 사용할 엔진을 자동으로 선택한다.
  - clova: HyperCLOVA X 임베딩 API (기본값, 1단계와 2단계)
  - local: 로컬 임베딩 서버 (3단계)

외부에서는 embedding_service 객체를 임포트하여 사용한다.
엔진 전환 시 이 파일 외에 수정할 코드가 없다.
"""

import asyncio
import httpx
from config import config


# ─────────────────────────────────────────────
# HyperCLOVA X 임베딩 엔진 (기존 코드 유지)
# ─────────────────────────────────────────────

class HyperClovaXEmbeddingService:
    """HyperCLOVA X 임베딩 API를 호출하는 서비스."""

    BASE_URL = "https://clovastudio.stream.ntruss.com/testapp/v1/api-tools"
    MODEL = "clir-sts-dolphin"
    VECTOR_SIZE = 1024

    def __init__(self):
        self.headers = {
            "X-NCP-CLOVASTUDIO-API-KEY": config.CLOVA_API_KEY,
            "X-NCP-APIGW-API-KEY": config.CLOVA_API_GATEWAY_KEY,
            "Content-Type": "application/json",
        }

    async def embed(self, text: str) -> list[float]:
        url = f"{self.BASE_URL}/embedding/{self.MODEL}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url, headers=self.headers, json={"text": text}
            )
            response.raise_for_status()
            data = response.json()
        return data["result"]["embedding"]

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 10,
    ) -> list[list[float]]:
        embeddings = []
        total = len(texts)
        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await asyncio.gather(
                *[self.embed(text) for text in batch]
            )
            embeddings.extend(batch_embeddings)
            print(f"임베딩 진행: {min(i + batch_size, total)}/{total}")
            if i + batch_size < total:
                await asyncio.sleep(0.5)
        return embeddings


# ─────────────────────────────────────────────
# 로컬 임베딩 서버 엔진
# ─────────────────────────────────────────────

class LocalEmbeddingService:
    """
    제11장에서 구축한 로컬 임베딩 서버를 호출하는 서비스.

    base_url로 임베딩 서버의 주소를 지정한다.
    Docker Compose 환경에서는 http://embedding-server:8001을 사용한다.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.VECTOR_SIZE = None  # 서버에 쿼리하여 결정
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """
        첫 호출 시 서버에서 벡터 차원을 확인한다.
        매 호출마다 실행하지 않도록 플래그를 사용한다.
        """
        if self._initialized:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/info")
            response.raise_for_status()
            data = response.json()
            self.VECTOR_SIZE = data["dimension"]
            print(
                f"[임베딩] 로컬 서버 연결 확인: {self.base_url} "
                f"(벡터 차원: {self.VECTOR_SIZE})"
            )
        self._initialized = True

    async def embed(self, text: str) -> list[float]:
        """단일 텍스트를 임베딩 벡터로 변환한다."""
        await self._ensure_initialized()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/embed",
                json={"text": text},
            )
            response.raise_for_status()
            data = response.json()

        return data["embedding"]

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[list[float]]:
        """
        여러 텍스트를 배치 단위로 임베딩한다.
        로컬 서버는 배치 API를 지원하므로 한 번의 요청으로 처리한다.
        """
        await self._ensure_initialized()

        all_embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/embed/batch",
                    json={"texts": batch},
                )
                response.raise_for_status()
                data = response.json()

            all_embeddings.extend(data["embeddings"])
            print(f"임베딩 진행: {min(i + batch_size, total)}/{total}")

        return all_embeddings


# ─────────────────────────────────────────────
# 엔진 선택 및 싱글톤 인스턴스 생성
# ─────────────────────────────────────────────

def _create_embedding_service():
    """
    환경 변수 EMBEDDING_PROVIDER에 따라 적절한 임베딩 서비스 인스턴스를 생성한다.
    """
    provider = config.EMBEDDING_PROVIDER.lower()

    if provider == "clova":
        print("[임베딩] HyperCLOVA X 임베딩 API 사용")
        return HyperClovaXEmbeddingService()

    elif provider == "local":
        base_url = config.EMBEDDING_BASE_URL
        if not base_url:
            raise ValueError(
                "EMBEDDING_PROVIDER가 'local'이면 EMBEDDING_BASE_URL을 설정해야 합니다."
            )
        print(f"[임베딩] 로컬 임베딩 서버 사용: {base_url}")
        return LocalEmbeddingService(base_url=base_url)

    else:
        raise ValueError(
            f"알 수 없는 EMBEDDING_PROVIDER 값: '{provider}'\n"
            "허용 값: clova, local"
        )


# 외부에서 임포트하여 사용하는 싱글톤 인스턴스
embedding_service = _create_embedding_service()
