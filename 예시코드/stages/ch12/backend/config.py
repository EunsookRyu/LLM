# config.py
# 가이드 참조: chapter12_multi_engine.md L276–L308
# Ch12 시점: 다중 엔진 설정 추가
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # HyperCLOVA X API
    CLOVA_API_KEY: str = os.getenv("CLOVA_API_KEY", "")
    CLOVA_API_GATEWAY_KEY: str = os.getenv("CLOVA_API_GATEWAY_KEY", "")

    # Qdrant
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "documents")

    # 임베딩
    EMBEDDING_VECTOR_SIZE: int = int(os.getenv("EMBEDDING_VECTOR_SIZE", "1024"))

    # LLM 서버 설정
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "clova")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "")

    # 임베딩 서버 설정
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "clova")
    EMBEDDING_BASE_URL: str = os.getenv("EMBEDDING_BASE_URL", "")


config = Config()
