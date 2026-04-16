# embedding-server/main.py
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import torch

# 전역 모델 객체
model: SentenceTransformer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 시 모델을 로드하고, 종료 시 메모리를 해제한다."""
    global model

    model_path = os.getenv("MODEL_PATH", "/models/bge-m3")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"임베딩 모델 로드 중: {model_path}")
    print(f"사용 디바이스: {device}")

    model = SentenceTransformer(
        model_path,
        local_files_only=True,
        device=device
    )
    print("임베딩 모델 로드 완료")
    print(f"벡터 차원: {model.get_sentence_embedding_dimension()}")

    yield

    # 서버 종료 시 메모리 해제
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    print("임베딩 모델 메모리 해제 완료")


app = FastAPI(
    title="NYSC 임베딩 서버",
    description="BGE-M3 기반 텍스트 임베딩 API",
    version="1.0.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────
# 요청/응답 모델
# ─────────────────────────────────────────────

class EmbedRequest(BaseModel):
    text: str


class EmbedResponse(BaseModel):
    embedding: list[float]
    model: str = "bge-m3"
    dimension: int


class BatchEmbedRequest(BaseModel):
    texts: list[str]


class BatchEmbedResponse(BaseModel):
    embeddings: list[list[float]]
    model: str = "bge-m3"
    count: int


# ─────────────────────────────────────────────
# 엔드포인트
# ─────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
    }


@app.get("/info")
def model_info():
    if model is None:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다.")
    return {
        "model": "bge-m3",
        "dimension": model.get_sentence_embedding_dimension(),
        "device": str(next(model.parameters()).device),
    }


@app.post("/embed", response_model=EmbedResponse)
def embed_text(request: EmbedRequest):
    """
    단일 텍스트를 임베딩 벡터로 변환한다.
    """
    if model is None:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다.")

    if not request.text.strip():
        raise HTTPException(status_code=400, detail="빈 텍스트는 처리할 수 없습니다.")

    embedding = model.encode(
        request.text,
        normalize_embeddings=True,
        show_progress_bar=False,
    ).tolist()

    return EmbedResponse(
        embedding=embedding,
        dimension=len(embedding),
    )


@app.post("/embed/batch", response_model=BatchEmbedResponse)
def embed_batch(request: BatchEmbedRequest):
    """여러 텍스트를 한 번에 임베딩 벡터로 변환한다."""
    if model is None:
        raise HTTPException(status_code=503, detail="모델이 로드되지 않았습니다.")

    if not request.texts:
        raise HTTPException(status_code=400, detail="텍스트 목록이 비어 있습니다.")

    # 빈 텍스트 필터링
    filtered_texts = [t.strip() for t in request.texts]
    if not all(filtered_texts):
        raise HTTPException(
            status_code=400,
            detail="목록에 빈 텍스트가 포함되어 있습니다."
        )

    embeddings = model.encode(
        filtered_texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=32,
    ).tolist()

    return BatchEmbedResponse(
        embeddings=embeddings,
        count=len(embeddings),
    )
