# main.py
import time
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, documents
from logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="내부 문서 AI 챗봇 API",
    description="HyperCLOVA X 기반 내부 업무 RAG 챗봇 API",
    version="3.0.0",
)

# CORS 설정
# 프론트엔드(Streamlit, NextChat 등)에서의 API 요청을 허용한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 HTTP 요청의 메서드, 경로, 소요 시간을 로깅한다."""
    start = time.time()
    response = await call_next(request)
    elapsed = time.time() - start
    logger.info(
        "%s %s → %d (%.3fs)",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


# 라우터 등록
app.include_router(chat.router)
app.include_router(documents.router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "내부 문서 AI 챗봇 API가 실행 중입니다."}


@app.get("/health")
async def health_check():
    """상세 헬스체크: Qdrant, LLM, 임베딩 서버 연결 상태를 확인한다."""
    import httpx
    from config import settings

    checks = {}

    # Qdrant 연결 확인
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/healthz"
            )
            checks["qdrant"] = "healthy" if r.status_code == 200 else "unhealthy"
    except Exception:
        checks["qdrant"] = "unreachable"

    # LLM 서버 연결 확인 (Ollama/vLLM)
    if settings.LLM_PROVIDER != "clova" and settings.LLM_BASE_URL:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{settings.LLM_BASE_URL}/api/tags")
                checks["llm"] = "healthy" if r.status_code == 200 else "unhealthy"
        except Exception:
            checks["llm"] = "unreachable"

    # 임베딩 서버 연결 확인 (Local)
    if settings.EMBEDDING_PROVIDER == "local" and settings.EMBEDDING_BASE_URL:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{settings.EMBEDDING_BASE_URL}/health")
                checks["embedding"] = "healthy" if r.status_code == 200 else "unhealthy"
        except Exception:
            checks["embedding"] = "unreachable"

    overall = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
