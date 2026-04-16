# config.py
# 가이드 참조: chapter3_python.md L203–L221 (3장에서 생성, 4장까지 동일)
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # HyperCLOVA X API
    CLOVA_API_KEY: str = os.getenv("CLOVA_API_KEY", "")
    CLOVA_API_GATEWAY_KEY: str = os.getenv("CLOVA_API_GATEWAY_KEY", "")
    CLOVA_REQUEST_ID: str = os.getenv("CLOVA_REQUEST_ID", "")

    # Qdrant
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = int(os.getenv("QDRANT_PORT", "6333"))

config = Config()
