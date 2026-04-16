# config.py
# 가이드 참조: chapter7_qdrant.md L373–L376, L551–L556
# Ch07 시점: ch04 config에 QDRANT + EMBEDDING 설정 추가
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # HyperCLOVA X API (ch03에서 도입)
    CLOVA_API_KEY: str = os.getenv("CLOVA_API_KEY", "")
    CLOVA_API_GATEWAY_KEY: str = os.getenv("CLOVA_API_GATEWAY_KEY", "")
    CLOVA_REQUEST_ID: str = os.getenv("CLOVA_REQUEST_ID", "")

    # Qdrant 벡터 데이터베이스 (ch07에서 추가)
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "documents")

    # 임베딩 설정 (ch07에서 추가)
    EMBEDDING_VECTOR_SIZE: int = int(os.getenv("EMBEDDING_VECTOR_SIZE", "1024"))


config = Config()
