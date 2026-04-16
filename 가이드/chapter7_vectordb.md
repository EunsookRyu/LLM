# 제7장. 벡터 데이터베이스 구축

## 7.1 이 장의 목표

제6장에서 벡터 데이터베이스가 무엇인지, 왜 필요한지 이해했다. 이 장에서는 실제로 Qdrant를 Python 코드로 다루며 데이터를 저장하고 검색하는 실습을 진행한다.

제5장에서 Docker Compose에 Qdrant 서비스를 이미 포함시켜 두었으므로, 별도 설치 없이 바로 실습을 시작할 수 있다. Qdrant의 기본 사용법을 익힌 뒤, 애플리케이션에서 사용할 임베딩 서비스 모듈과 벡터 저장소 서비스 모듈을 작성한다.

---

## 7.2 Qdrant 기본 사용법

### 서비스 확인

제5장의 Docker Compose로 전체 서비스를 실행했다면 Qdrant가 이미 포트 6333에서 동작 중이다.

```bash
# 서비스 상태 확인
docker compose ps

# Qdrant 상태만 확인
curl http://localhost:6333/healthz
```

브라우저에서 `http://localhost:6333/dashboard`에 접속하면 Qdrant의 웹 대시보드를 확인할 수 있다. 컬렉션 목록, 저장된 벡터 수, 검색 테스트 등을 시각적으로 수행할 수 있어 개발 중에 매우 유용하다.

Qdrant가 실행되지 않은 상태라면 배포 디렉터리에서 개별 서비스만 시작할 수 있다.

```bash
cd deploy
docker compose up -d qdrant
```

### Python 클라이언트 설치

```bash
pip install qdrant-client
```

### 서버 연결

```python
from qdrant_client import QdrantClient

# Qdrant 서버에 연결
# Docker Compose 환경에서는 호스트를 'qdrant'로 설정
# 로컬 직접 실행 시에는 'localhost'로 설정
client = QdrantClient(host="localhost", port=6333)

# 서버 연결 확인
print(client.get_collections())
```

### 컬렉션 생성

Qdrant에서 컬렉션을 생성할 때는 벡터의 차원 수와 거리 계산 방식을 반드시 지정해야 한다. 차원 수는 사용하는 임베딩 모델의 출력 벡터 차원과 일치해야 한다.

HyperCLOVA X 임베딩 API와 BGE-M3 모델 모두 1024차원 벡터를 생성한다.

```python
from qdrant_client.models import Distance, VectorParams

COLLECTION_NAME = "documents"
VECTOR_SIZE = 1024  # 임베딩 모델의 출력 벡터 차원

# 컬렉션이 없는 경우에만 생성
if not client.collection_exists(COLLECTION_NAME):
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=Distance.COSINE
        )
    )
    print(f"컬렉션 '{COLLECTION_NAME}'이 생성되었습니다.")
else:
    print(f"컬렉션 '{COLLECTION_NAME}'이 이미 존재합니다.")

# 컬렉션 정보 확인
collection_info = client.get_collection(COLLECTION_NAME)
print(f"저장된 벡터 수: {collection_info.points_count}")
```

### 데이터 추가

Qdrant에서 저장 단위는 **포인트(point)**다. 각 포인트는 ID, 벡터, 페이로드(메타데이터에 해당)로 구성된다.

```python
from qdrant_client.models import PointStruct
import uuid

# 포인트 추가
client.upsert(
    collection_name=COLLECTION_NAME,
    points=[
        PointStruct(
            id=str(uuid.uuid4()),
            vector=[0.1, 0.2, 0.3, ...],   # 1024차원 벡터
            payload={
                "text": "출장비 정산은 출장 완료 후 7일 이내에 신청해야 합니다.",
                "source": "사내_규정집_2025.pdf",
                "page": 8,
                "category": "업무규정"
            }
        ),
        PointStruct(
            id=str(uuid.uuid4()),
            vector=[0.4, 0.5, 0.6, ...],
            payload={
                "text": "연차 휴가는 1년 미만 근무 시 매월 1일씩 발생합니다.",
                "source": "사내_규정집_2025.pdf",
                "page": 15,
                "category": "규정"
            }
        ),
        PointStruct(
            id=str(uuid.uuid4()),
            vector=[0.7, 0.8, 0.9, ...],
            payload={
                "text": "보안 교육은 매 분기 1회 의무적으로 이수해야 합니다.",
                "source": "업무_매뉴얼.pdf",
                "page": 3,
                "category": "업무규정"
            }
        ),
    ]
)
```

`upsert`는 update + insert의 의미로, 같은 ID의 포인트가 이미 존재하면 업데이트하고 없으면 새로 추가한다.

Qdrant의 포인트 ID는 양의 정수 또는 UUID 문자열이어야 한다. 임의의 문자열은 ID로 사용할 수 없다. UUID를 사용하면 고유성을 보장하면서 충돌 없이 ID를 생성할 수 있다.

### 유사도 검색

```python
# 기본 유사도 검색
results = client.search(
    collection_name=COLLECTION_NAME,
    query_vector=[0.15, 0.25, 0.35, ...],  # 질문의 임베딩 벡터
    limit=3,
    with_payload=True   # 페이로드(메타데이터) 함께 반환
)

for result in results:
    print(f"유사도 점수: {result.score:.4f}")
    print(f"텍스트: {result.payload['text']}")
    print(f"출처: {result.payload['source']} ({result.payload['page']}페이지)")
    print()
```

Qdrant에서 `score`는 코사인 유사도 값이다. 1에 가까울수록 유사도가 높다.

### 메타데이터 필터링

특정 조건을 만족하는 문서만 검색할 수 있다.

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# 특정 카테고리에서만 검색
results = client.search(
    collection_name=COLLECTION_NAME,
    query_vector=[0.15, 0.25, 0.35, ...],
    query_filter=Filter(
        must=[
            FieldCondition(
                key="category",
                match=MatchValue(value="업무규정")
            )
        ]
    ),
    limit=3,
    with_payload=True
)
```

`must` 조건 안의 모든 조건을 만족하는 포인트만 검색한다. 여러 조건을 결합할 수도 있다.

```python
from qdrant_client.models import Range

# 특정 파일의 특정 페이지 이후 내용만 검색
results = client.search(
    collection_name=COLLECTION_NAME,
    query_vector=[0.15, 0.25, 0.35, ...],
    query_filter=Filter(
        must=[
            FieldCondition(
                key="source",
                match=MatchValue(value="사내_규정집_2025.pdf")
            ),
            FieldCondition(
                key="page",
                range=Range(gte=10)   # 10페이지 이상
            )
        ]
    ),
    limit=3,
    with_payload=True
)
```

### 대량 데이터 배치 추가

문서가 많을 때는 한 번에 모든 포인트를 추가하면 메모리 부담이 크다. 배치 단위로 나누어 추가하는 것이 좋다.

```python
def batch_upsert(
    client: QdrantClient,
    collection_name: str,
    points: list[PointStruct],
    batch_size: int = 100
) -> None:
    """포인트를 배치 단위로 나누어 추가한다."""
    total = len(points)
    for i in range(0, total, batch_size):
        batch = points[i:i + batch_size]
        client.upsert(collection_name=collection_name, points=batch)
        print(f"진행: {min(i + batch_size, total)}/{total}")
    print("모든 데이터 추가 완료")
```

### 데이터 삭제

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# ID로 삭제
client.delete(
    collection_name=COLLECTION_NAME,
    points_selector=["포인트_ID_1", "포인트_ID_2"]
)

# 조건으로 삭제 (특정 파일의 모든 포인트 삭제)
client.delete(
    collection_name=COLLECTION_NAME,
    points_selector=Filter(
        must=[
            FieldCondition(
                key="source",
                match=MatchValue(value="구버전_자료.pdf")
            )
        ]
    )
)
```

> **참고 — ChromaDB**: 벡터 데이터베이스를 처음 접한다면 ChromaDB로 빠르게 실습해 볼 수도 있다. `pip install chromadb`만으로 설치되고, 별도 서버 없이 Python 프로세스 안에서 동작한다. `client = chromadb.PersistentClient(path="./chroma_db")`로 로컬 파일 기반 저장소를 생성하고, `collection.add()`와 `collection.query()`로 저장·검색이 가능하다. 다만 이 가이드에서는 운영 환경을 염두에 두고 Qdrant를 사용한다.

---

## 7.3 임베딩 서비스 모듈 작성

벡터 데이터베이스에 데이터를 저장하고 검색하려면 텍스트를 벡터로 변환하는 임베딩 모델이 필요하다. 제4장에서 LLM 서비스를 독립 모듈로 분리했던 것처럼, 임베딩 서비스도 별도 모듈로 분리한다. 나중에 HyperCLOVA X 임베딩 API를 로컬 BGE-M3 서버로 교체할 때 이 파일만 수정하면 된다.

### HyperCLOVA X 임베딩 API

CLOVA Studio는 텍스트를 벡터로 변환하는 임베딩 API도 제공한다. 채팅 API와 마찬가지로 HTTP 요청으로 호출한다.

임베딩 API의 엔드포인트는 다음과 같다.

```
POST https://clovastudio.stream.ntruss.com/testapp/v1/api-tools/embedding/clir-sts-dolphin
```

요청 형식은 다음과 같다.

```json
{
  "text": "임베딩할 텍스트"
}
```

응답 형식은 다음과 같다.

```json
{
  "status": {
    "code": "20000",
    "message": "OK"
  },
  "result": {
    "embedding": [0.023, -0.045, 0.112, ...]
  }
}
```

`result.embedding`이 텍스트를 변환한 벡터다.

### 임베딩 서비스 모듈

```python
# services/embeddings.py
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
```

`embed_batch`에서 `asyncio.gather`를 사용하면 배치 안의 여러 요청을 순차적이 아닌 병렬로 처리한다. 배치 크기가 10이라면 10개의 요청이 동시에 발송되어 처리 시간이 크게 단축된다.

`config.py`에 임베딩 관련 설정을 추가한다.

```python
# config.py에 추가
EMBEDDING_VECTOR_SIZE: int = int(os.getenv("EMBEDDING_VECTOR_SIZE", "1024"))
```

---

## 7.4 벡터 데이터베이스 서비스 모듈 작성

벡터 데이터베이스 접근 로직도 독립 모듈로 분리한다. Qdrant 클라이언트를 직접 사용하는 코드가 여러 파일에 흩어지면 나중에 수정이 어렵다. 모든 벡터 데이터베이스 작업을 `services/vector_store.py` 한 곳에서 관리한다.

```python
# services/vector_store.py
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
from config import config


class VectorStoreService:
    """
    Qdrant 벡터 데이터베이스와의 모든 상호작용을 담당하는 서비스 클래스.
    """

    def __init__(self):
        self.client = QdrantClient(
            host=config.QDRANT_HOST,
            port=config.QDRANT_PORT
        )
        self.collection_name = config.QDRANT_COLLECTION_NAME
        self.vector_size = config.EMBEDDING_VECTOR_SIZE
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """컬렉션이 없으면 생성한다."""
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
            print(f"컬렉션 '{self.collection_name}' 생성 완료")

    def add_documents(
        self,
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict]
    ) -> list[str]:
        """
        문서 텍스트, 임베딩, 메타데이터를 함께 저장한다.
        생성된 포인트 ID 목록을 반환한다.
        """
        if not (len(texts) == len(embeddings) == len(metadatas)):
            raise ValueError(
                "texts, embeddings, metadatas의 길이가 동일해야 합니다."
            )

        points = []
        ids = []

        for text, embedding, metadata in zip(texts, embeddings, metadatas):
            point_id = str(uuid.uuid4())
            ids.append(point_id)

            # 검색 결과에서 텍스트를 바로 사용할 수 있도록
            # 원본 텍스트도 페이로드에 포함시킨다.
            payload = {"text": text, **metadata}

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            )

        # 배치 단위로 나누어 업로드한다.
        batch_size = 100
        for i in range(0, len(points), batch_size):
            self.client.upsert(
                collection_name=self.collection_name,
                points=points[i:i + batch_size]
            )

        return ids

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filter_conditions: dict | None = None
    ) -> list[dict]:
        """
        쿼리 벡터와 유사한 문서를 검색하여 반환한다.

        반환 형식:
        [
            {
                "text": "문서 텍스트",
                "score": 0.95,
                "source": "파일명.pdf",
                ...메타데이터
            },
            ...
        ]
        """
        search_filter = None
        if filter_conditions:
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                    for key, value in filter_conditions.items()
                ]
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            query_filter=search_filter,
            limit=top_k,
            with_payload=True
        )

        return [
            {
                "text": result.payload.get("text", ""),
                "score": result.score,
                **{
                    k: v for k, v in result.payload.items()
                    if k != "text"
                }
            }
            for result in results
        ]

    def delete_by_source(self, source: str) -> None:
        """특정 파일에서 추출한 모든 문서 조각을 삭제한다."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="source",
                        match=MatchValue(value=source)
                    )
                ]
            )
        )

    def get_collection_info(self) -> dict:
        """컬렉션의 기본 정보를 반환한다."""
        info = self.client.get_collection(self.collection_name)
        return {
            "name": self.collection_name,
            "points_count": info.points_count,
            "vector_size": self.vector_size
        }


# 싱글톤 인스턴스
vector_store = VectorStoreService()
```

`config.py`에 Qdrant 관련 설정을 추가한다.

```python
# config.py에 추가
QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "documents")
```

`.env` 파일에도 추가한다.

```
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=documents
```

Docker Compose 환경에서는 `QDRANT_HOST`를 서비스 이름인 `qdrant`로 설정한다. 로컬에서 직접 실행할 때는 `localhost`를 사용한다. 제5장의 `docker-compose.yml`에서 백엔드의 `QDRANT_HOST=qdrant` 환경 변수가 이미 설정되어 있으므로 별도 수정은 필요 없다.

---

## 7.5 동작 확인 테스트

벡터 데이터베이스와 임베딩 서비스가 정상적으로 동작하는지 확인하는 테스트 스크립트를 작성한다.

```python
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
```

Qdrant가 실행 중인 상태에서 테스트 스크립트를 실행한다.

```bash
cd backend
python test_vector_store.py
```

다음과 같은 출력이 나타나면 정상 동작하는 것이다.

```
=== 임베딩 생성 테스트 ===
임베딩 진행: 3/3
생성된 벡터 수: 3
벡터 차원: 1024

=== 벡터 저장 테스트 ===
저장된 포인트 ID: ['uuid-1', 'uuid-2', 'uuid-3']

=== 유사도 검색 테스트 ===
검색 쿼리: 출장비 정산 기한이 어떻게 되나요?

결과 1:
  유사도 점수: 0.8912
  텍스트: 출장비 정산은 출장 완료 후 7일 이내에 신청해야 합니다.
  출처: 교육프로그램_안내_2025.pdf (8페이지)

결과 2:
  유사도 점수: 0.7651
  텍스트: 보안 교육은 매 분기 1회 의무적으로 이수해야 합니다.
  출처: 운영매뉴얼.pdf (3페이지)
```

"업무규정"과 관련된 문서가 상위에 검색되었다면 임베딩과 유사도 검색이 올바르게 동작하는 것이다. Qdrant 대시보드(`http://localhost:6333/dashboard`)에서도 `documents` 컬렉션에 3개의 포인트가 저장된 것을 확인할 수 있다.

---

## 7.6 Docker Compose 환경 변수 업데이트

제5장의 `docker-compose.yml`에서 백엔드 서비스에 Qdrant 환경 변수가 이미 설정되어 있다. 이 장에서 추가된 설정을 반영한다.

```yaml
# docker-compose.yml의 backend 서비스 environment에 추가
environment:
  - CLOVA_API_KEY=${CLOVA_API_KEY}
  - CLOVA_API_GATEWAY_KEY=${CLOVA_API_GATEWAY_KEY}
  - QDRANT_HOST=qdrant
  - QDRANT_PORT=6333
  - QDRANT_COLLECTION_NAME=${QDRANT_COLLECTION_NAME:-documents}
  - EMBEDDING_VECTOR_SIZE=${EMBEDDING_VECTOR_SIZE:-1024}
```

`.env.example`도 업데이트한다.

```
# .env.example

# HyperCLOVA X API
CLOVA_API_KEY=여기에_API_키를_입력하세요
CLOVA_API_GATEWAY_KEY=여기에_API_Gateway_키를_입력하세요

# Qdrant 설정
QDRANT_COLLECTION_NAME=documents

# 임베딩 설정
EMBEDDING_VECTOR_SIZE=1024
```

---

## 7.7 현재까지의 파일 구조

```
backend/
├── Dockerfile
├── requirements.txt
├── main.py
├── config.py
├── test_vector_store.py           # 동작 확인 스크립트
├── routers/
│   ├── __init__.py
│   └── chat.py                    # /v1/chat/completions
├── services/
│   ├── __init__.py
│   ├── llm.py                     # LLM 서비스 (교체 대상)
│   ├── conversation.py            # 메시지 가공 유틸리티
│   ├── embeddings.py              # 임베딩 서비스 (교체 대상)
│   └── vector_store.py            # 벡터 DB 서비스
├── models/
│   ├── __init__.py
│   └── chat.py                    # OpenAI 호환 모델
│
├── .env
├── .env.example
└── .gitignore
```

`requirements.txt`에 새로운 패키지를 추가한다.

```
# requirements.txt
fastapi==0.111.0
uvicorn[standard]==0.30.1
httpx==0.27.0
python-dotenv==1.0.1
pydantic==2.7.4
qdrant-client==1.9.1
```

변경 사항을 커밋한다.

```bash
cd backend
git add .
git commit -m "벡터 데이터베이스 및 임베딩 서비스 모듈 추가"
```

---

이것으로 제7장의 내용을 마친다. Qdrant 벡터 데이터베이스의 기본 사용법을 익히고, 임베딩 서비스와 벡터 저장소 서비스를 독립 모듈로 구현했다. 다음 장에서는 실제 문서 파일을 불러와 청킹하고 벡터 데이터베이스에 저장하는 문서 인덱싱 파이프라인 전체를 구축한다.
