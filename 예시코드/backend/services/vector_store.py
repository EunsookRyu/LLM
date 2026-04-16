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
