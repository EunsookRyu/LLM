# 제11장. 로컬 LLM 서빙 서버 구축

## 11.1 이 장의 목표

제10장에서 모델 파일을 내려받고 Ollama를 설치했다. 이 장에서는 두 가지 서빙 환경을 단계적으로 구축한다.

먼저 Ollama를 이용해 개발 및 테스트 환경을 설정한다. Ollama는 설치가 간단하고 macOS와 Linux, Windows를 모두 지원하므로 기능 검증과 빠른 반복 개발에 적합하다.

그 다음 vLLM을 이용한 운영 환경을 구축한다. vLLM은 동시 요청 처리 성능이 뛰어나 여러 사용자가 접속하는 실제 서비스 환경에 적합하다.

마지막으로 로컬 임베딩 서버를 구축하여 임베딩 생성도 외부 API 의존 없이 처리할 수 있도록 한다.

---

## 11.2 Ollama 서버 상세 설정

제10장에서 Ollama 설치와 기본 동작 확인까지 마쳤다. 이 절에서는 서버 운영에 필요한 상세 설정을 다룬다.

### 모델 관리 명령어

Ollama에서 모델을 관리하는 주요 명령어를 정리한다.

내려받은 모델 목록을 확인한다.

```bash
ollama list
```

새 모델을 내려받는다.

```bash
ollama pull exaone3.5:7.8b
```

Hugging Face에서 내려받은 GGUF 파일을 Ollama에 직접 등록할 수도 있다. 이 방법은 Ollama에서 공식으로 제공하지 않는 모델을 사용하거나, 특정 양자화 버전을 직접 지정하고 싶을 때 유용하다.

먼저 Modelfile을 작성한다.

```
# Modelfile
FROM /root/models/exaone-3.5-7.8b/EXAONE-3.5-7.8B-Instruct-Q4_K_M.gguf

PARAMETER temperature 0.7
PARAMETER top_p 0.8
PARAMETER top_k 40
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096

SYSTEM "당신은 조직의 내부 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다. 정확하고 이해하기 쉬운 언어로 답변합니다."
```

Modelfile을 기반으로 모델을 생성한다.

```bash
ollama create exaone-custom -f Modelfile
```

생성된 모델을 실행한다.

```bash
ollama run exaone-custom
```

모델을 삭제한다.

```bash
ollama rm exaone-custom
```

### Ollama API 상세

Ollama는 두 가지 API 형식을 제공한다. 자체 형식과 OpenAI 호환 형식이다. 이 가이드에서는 나중에 vLLM으로 교체할 때의 일관성을 위해 OpenAI 호환 형식을 사용한다. 백엔드의 `services/llm.py`가 이 형식으로 호출하며, 프론트엔드 → 백엔드(`/v1/chat/completions`) → Ollama(`/v1/chat/completions`) 경로로 요청이 흐른다.

OpenAI 호환 API로 채팅 완성을 요청하는 예시다.

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "exaone3.5:7.8b",
    "messages": [
      {
        "role": "system",
        "content": "당신은 조직의 내부 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다."
      },
      {
        "role": "user",
        "content": "연차 휴가 신청 절차를 간단히 설명해주세요."
      }
    ],
    "temperature": 0.7,
    "max_tokens": 512,
    "stream": false
  }'
```

스트리밍 방식으로 요청하려면 `"stream": true`로 변경한다. 응답은 Server-Sent Events 형식으로 전달된다.

### Ollama 환경 변수 설정

Ollama의 동작을 환경 변수로 제어할 수 있다.

`OLLAMA_HOST`는 Ollama 서버가 수신할 주소를 지정한다. 기본값은 `127.0.0.1:11434`다. Docker 컨테이너나 다른 머신에서 접근할 수 있도록 하려면 `0.0.0.0:11434`로 설정해야 한다.

`OLLAMA_MODELS`는 모델 파일을 저장하는 경로를 지정한다. 기본값은 `~/.ollama/models`다.

`OLLAMA_NUM_PARALLEL`은 동시에 처리할 요청 수를 지정한다. 기본값은 GPU 메모리에 따라 자동으로 결정된다.

`OLLAMA_MAX_LOADED_MODELS`는 메모리에 동시에 올릴 수 있는 모델 수를 지정한다. 기본값은 1이다.

Linux에서 systemd 서비스로 실행 중인 경우, 환경 변수를 다음과 같이 설정한다.

```bash
sudo systemctl edit ollama
```

에디터가 열리면 다음 내용을 추가한다.

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_NUM_PARALLEL=2"
```

변경 사항을 적용한다.

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Docker로 Ollama 실행

Docker Compose 환경에서 Ollama를 실행하는 방법이다. `docker-compose.yml`에 다음 서비스를 추가한다.

GPU를 사용하는 경우의 설정이다.

```yaml
  ollama:
    image: ollama/ollama:latest
    container_name: chatbot-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    networks:
      - chatbot-network
```

GPU가 없는 환경에서는 `deploy.resources` 항목을 제거한다.

```yaml
  ollama:
    image: ollama/ollama:latest
    container_name: chatbot-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    networks:
      - chatbot-network
```

Ollama 컨테이너를 처음 시작한 후, 모델을 컨테이너 안으로 내려받아야 한다.

```bash
# Ollama 컨테이너 시작
docker compose up -d ollama

# 컨테이너 안에서 모델 내려받기
docker exec chatbot-ollama ollama pull exaone3.5:7.8b
```

또는 로컬에서 이미 내려받은 모델 파일을 볼륨으로 마운트하는 방법도 있다.

```yaml
    volumes:
      - ~/models:/root/.ollama/models   # 로컬 모델 경로를 마운트
```

---

## 11.3 vLLM 서버 구축

vLLM은 운영 환경에서 높은 처리량을 제공하는 LLM 서빙 프레임워크다. Docker 이미지로 간편하게 실행할 수 있으며, OpenAI 호환 API를 기본으로 제공한다.

### vLLM의 핵심 기술 이해

vLLM이 높은 처리량을 달성하는 핵심 기술은 PagedAttention이다. 기존 LLM 추론 방식에서는 각 요청의 KV 캐시를 연속된 메모리 블록에 저장해야 했기 때문에, VRAM의 상당 부분이 낭비되거나 처리할 수 있는 동시 요청 수가 제한되었다. PagedAttention은 운영체제의 가상 메모리 페이징 기법을 KV 캐시에 적용하여 VRAM을 훨씬 효율적으로 활용한다. 그 결과 같은 GPU 메모리로 더 많은 요청을 동시에 처리할 수 있다.

### vLLM Docker 이미지

vLLM은 공식 Docker 이미지를 제공한다. CUDA 버전에 맞는 이미지를 선택한다.

```bash
# CUDA 12.1 환경
docker pull vllm/vllm-openai:latest
```

### docker-compose.yml에 vLLM 추가

```yaml
  vllm:
    image: vllm/vllm-openai:latest
    container_name: chatbot-vllm
    ports:
      - "8080:8000"
    volumes:
      - ~/models:/models          # 모델 파일 경로
    command: [
      "--model", "/models/exaone-3.5-7.8b-hf",
      "--served-model-name", "exaone",
      "--host", "0.0.0.0",
      "--port", "8000",
      "--max-model-len", "4096",
      "--gpu-memory-utilization", "0.90"
    ]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 10
      start_period: 120s
    networks:
      - chatbot-network
```

주요 실행 인자의 의미를 설명한다.

`--model`은 로드할 모델의 경로 또는 Hugging Face 모델 ID를 지정한다. 컨테이너 안의 경로를 사용한다.

`--served-model-name`은 API에서 사용하는 모델 이름을 지정한다. 이 이름으로 API를 호출한다.

`--max-model-len`은 처리할 수 있는 최대 컨텍스트 길이다. VRAM이 제한된 환경에서는 이 값을 줄여 메모리 사용량을 낮출 수 있다.

`--gpu-memory-utilization`은 GPU 메모리의 몇 퍼센트를 vLLM이 사용할지를 지정한다. 0.9는 90%를 의미한다. 나머지 10%는 운영체제와 기타 프로세스를 위해 남겨둔다.

### vLLM 동작 확인

vLLM 서버가 시작되면 OpenAI API 형식으로 테스트한다. vLLM의 기본 포트는 8000이며, Docker Compose 설정에서 호스트의 8080 포트로 노출했다.

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "exaone",
    "messages": [
      {"role": "user", "content": "재택근무 신청 방법을 알려주세요."}
    ],
    "max_tokens": 100,
    "temperature": 0.7
  }'
```

정상적인 응답이 돌아오면 vLLM 서버가 준비된 것이다.

사용 가능한 모델 목록을 확인한다.

```bash
curl http://localhost:8080/v1/models
```

### VRAM 부족 시 대응 방법

vLLM 시작 시 VRAM 부족으로 오류가 발생하는 경우, 다음 방법을 순서대로 시도한다.

먼저 `--max-model-len` 값을 줄인다. 4096에서 2048로 낮추면 KV 캐시 크기가 줄어 메모리를 절약할 수 있다.

다음으로 `--gpu-memory-utilization` 값을 낮춘다. 0.90에서 0.85 정도로 조정한다.

그래도 부족하다면 양자화 수준이 더 높은 모델을 사용한다. AWQ 양자화 버전을 적용하면 메모리 사용량이 크게 줄어든다.

```yaml
    command: [
      "--model", "/models/exaone-3.5-7.8b-awq",
      "--served-model-name", "exaone",
      "--quantization", "awq",
      "--max-model-len", "2048",
      "--gpu-memory-utilization", "0.85"
    ]
```

---

## 11.4 로컬 임베딩 서버 구축

LLM 서버와 별도로, 텍스트 임베딩을 생성하는 서버를 구축한다. FastAPI로 간단한 HTTP 서버를 만들어 BGE-M3 모델을 서빙한다.

이 서버는 `services/embeddings.py`의 인터페이스와 맞도록 설계한다. URL 주소만 교체하면 기존 코드 변경 없이 HyperCLOVA X 임베딩 API를 대체할 수 있다. 벡터 차원이 동일(1024)하므로 Qdrant의 `documents` 컬렉션도 재생성할 필요가 없다.

### 임베딩 서버 코드

`deploy` 저장소 안에 별도의 폴더로 관리한다.

```bash
mkdir -p embedding-server
```

```python
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
```

### 임베딩 서버 의존성 및 Dockerfile

```
# embedding-server/requirements.txt
fastapi==0.111.0
uvicorn[standard]==0.30.1
sentence-transformers==3.0.1
torch==2.3.1
transformers==4.42.3
```

```dockerfile
# embedding-server/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# torch는 크기가 크므로 먼저 설치하여 캐싱 효과를 높인다.
RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
```

CPU 전용 이미지를 기본으로 한다. GPU를 사용하려면 베이스 이미지를 `pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime`으로 변경하고 torch 설치 명령을 제거한다.

### docker-compose.yml에 임베딩 서버 추가

```yaml
  embedding-server:
    build:
      context: ./embedding-server
      dockerfile: Dockerfile
    container_name: chatbot-embedding
    ports:
      - "8001:8001"
    volumes:
      - ~/models/bge-m3:/models/bge-m3:ro   # 읽기 전용으로 마운트
    environment:
      - MODEL_PATH=/models/bge-m3
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks:
      - chatbot-network
```

### 임베딩 서버 동작 확인

임베딩 서버가 시작된 후 API를 테스트한다.

```bash
# 서버 정보 확인
curl http://localhost:8001/info

# 단일 텍스트 임베딩
curl -X POST http://localhost:8001/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "연차 휴가는 근로기준법에 따라 근로자에게 부여되는 유급휴가이다."}'

# 배치 임베딩
curl -X POST http://localhost:8001/embed/batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["연차 휴가 규정", "출장비 정산 절차"]}'
```

응답에 `embedding` 필드가 포함되고 1024개의 숫자 배열이 반환된다면 정상 동작하는 것이다. 이 차원이 Qdrant `documents` 컬렉션의 설정과 일치하므로 기존 인덱싱 데이터와 호환된다.

---

## 11.5 서빙 환경 선택에 따른 docker-compose.yml 구성

Ollama(개발 환경)와 vLLM(운영 환경)을 모두 `docker-compose.yml`에 포함하되, 환경에 따라 선택적으로 실행할 수 있도록 구성한다.

두 가지 방법이 있다.

### 방법 1: 별도의 Compose 파일 사용

운영 환경용 `docker-compose.prod.yml`을 만들어 vLLM 설정을 포함시킨다. 개발 환경에서는 기본 `docker-compose.yml`만 사용하고, 운영 환경에서는 두 파일을 합쳐 실행한다.

```bash
# 개발 환경
docker compose up -d

# 운영 환경 (vLLM 적용)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 방법 2: 프로파일로 서비스 선택

Docker Compose의 프로파일 기능을 활용하면 특정 서비스를 선택적으로 실행할 수 있다.

```yaml
  ollama:
    profiles: ["dev", "ollama"]
    image: ollama/ollama:latest
    # ... 나머지 설정

  vllm:
    profiles: ["prod", "vllm"]
    image: vllm/vllm-openai:latest
    # ... 나머지 설정
```

프로파일을 지정하여 실행한다.

```bash
# Ollama 포함하여 실행 (개발 환경)
COMPOSE_PROFILES=dev docker compose up -d

# vLLM 포함하여 실행 (운영 환경)
COMPOSE_PROFILES=prod docker compose up -d
```

이 가이드에서는 방법 1을 사용한다. 파일을 분리하면 개발 환경과 운영 환경의 설정 차이가 명확하게 드러나 관리하기 쉽다.

### 최종 docker-compose.yml (개발 환경 기준)

제5장에서 구성한 3서비스(프론트엔드, 백엔드, Qdrant) 기반에 Ollama와 임베딩 서버를 추가하여 5서비스 구성이 된다.

```yaml
# docker-compose.yml
services:

  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    container_name: chatbot-frontend
    ports:
      - "8501:8501"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - chatbot-network

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: chatbot-backend
    ports:
      - "8000:8000"
    environment:
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
      - QDRANT_COLLECTION_NAME=${QDRANT_COLLECTION_NAME:-documents}
      - EMBEDDING_VECTOR_SIZE=${EMBEDDING_VECTOR_SIZE:-1024}
      # HyperCLOVA X API (2단계)
      - CLOVA_API_KEY=${CLOVA_API_KEY:-}
      - CLOVA_API_GATEWAY_KEY=${CLOVA_API_GATEWAY_KEY:-}
      # LLM 서버 설정 (3단계)
      - LLM_PROVIDER=${LLM_PROVIDER:-clova}
      - LLM_BASE_URL=${LLM_BASE_URL:-}
      - LLM_MODEL_NAME=${LLM_MODEL_NAME:-}
      # 임베딩 서버 설정 (3단계)
      - EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER:-clova}
      - EMBEDDING_BASE_URL=${EMBEDDING_BASE_URL:-}
    depends_on:
      qdrant:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    networks:
      - chatbot-network

  qdrant:
    image: qdrant/qdrant:v1.9.4
    container_name: chatbot-qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    networks:
      - chatbot-network

  ollama:
    image: ollama/ollama:latest
    container_name: chatbot-ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    networks:
      - chatbot-network

  embedding-server:
    build:
      context: ./embedding-server
      dockerfile: Dockerfile
    container_name: chatbot-embedding
    ports:
      - "8001:8001"
    volumes:
      - ${BGE_M3_PATH:-/tmp}:/models/bge-m3:ro
    environment:
      - MODEL_PATH=/models/bge-m3
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s
    networks:
      - chatbot-network

networks:
  chatbot-network:
    driver: bridge

volumes:
  qdrant_data:
  ollama_data:
```

`.env`에 새 환경 변수를 추가한다.

```
# .env

# HyperCLOVA X API (2단계에서 사용)
CLOVA_API_KEY=여기에_API_키를_입력하세요
CLOVA_API_GATEWAY_KEY=여기에_API_Gateway_키를_입력하세요

# Qdrant 설정
QDRANT_COLLECTION_NAME=documents

# 임베딩 설정
EMBEDDING_VECTOR_SIZE=1024

# LLM 서버 설정 (3단계에서 사용)
# clova: HyperCLOVA X API 사용
# ollama: 로컬 Ollama 서버 사용
# vllm: 로컬 vLLM 서버 사용
LLM_PROVIDER=clova
LLM_BASE_URL=http://ollama:11434/v1
LLM_MODEL_NAME=exaone3.5:7.8b

# 임베딩 서버 설정 (3단계에서 사용)
# clova: HyperCLOVA X 임베딩 API 사용
# local: 로컬 임베딩 서버 사용
EMBEDDING_PROVIDER=clova
EMBEDDING_BASE_URL=http://embedding-server:8001

# BGE-M3 모델 경로 (로컬 절대 경로)
BGE_M3_PATH=/home/사용자명/models/bge-m3
```

---

## 11.6 전체 서비스 기동 순서

모든 서비스를 처음 실행할 때 권장하는 순서다.

먼저 Qdrant를 실행하고 준비 완료를 확인한다.

```bash
cd deploy
docker compose up -d qdrant
docker compose logs -f qdrant
# "Qdrant is ready to accept connections" 메시지 확인 후 Ctrl+C
```

다음으로 Ollama를 실행하고 모델을 내려받는다.

```bash
docker compose up -d ollama
# 시작 완료까지 잠시 대기
sleep 15
docker exec chatbot-ollama ollama pull exaone3.5:7.8b
```

임베딩 서버를 실행한다. 모델 로드에 1분 정도 소요될 수 있다.

```bash
docker compose up -d embedding-server
docker compose logs -f embedding-server
# "임베딩 모델 로드 완료" 메시지 확인 후 Ctrl+C
```

백엔드와 프론트엔드를 실행한다.

```bash
docker compose up -d backend frontend
```

전체 서비스 상태를 확인한다.

```bash
docker compose ps
```

모든 서비스가 `running (healthy)` 상태여야 한다. 브라우저에서 `http://localhost:8501`에 접속하면 Streamlit 채팅 인터페이스가 나타난다.

---

## 11.7 현재까지의 파일 구조

```

├── docker-compose.yml          # 5서비스: 프론트엔드(Streamlit), 백엔드, Qdrant, Ollama, 임베딩
├── .env                        # 3단계 환경 변수 추가
├── .gitignore
└── embedding-server/           # 신규
    ├── Dockerfile
    ├── requirements.txt
    └── main.py

backend/           # 별도 저장소 (이전과 동일)
├── services/
│   ├── llm.py                  # 다음 장에서 교체
│   ├── embeddings.py           # 다음 장에서 교체
│   └── ...
└── ...

frontend/          # 별도 저장소 (변경 없음)
└── ...
```

변경 사항을 커밋한다.

```bash
# deploy 저장소
git add .
git commit -m "feat: Ollama, vLLM, 임베딩 서버 설정 추가

- Ollama 서비스: 개발용 LLM 서빙 (GPU/CPU)
- vLLM 설정: 운영용 고성능 서빙 (docker-compose.prod.yml)
- BGE-M3 임베딩 서버: FastAPI 기반, 1024차원 (documents 호환)
- 환경 변수: LLM_PROVIDER, EMBEDDING_PROVIDER로 전환 제어"
```

---

이것으로 제11장의 내용을 마친다. Ollama와 vLLM 서빙 서버를 구성하고, BGE-M3 기반의 로컬 임베딩 서버를 구축했다. 다음 장에서는 이 서버들을 실제로 백엔드에 연결하는 작업, 즉 `services/llm.py`와 `services/embeddings.py` 두 파일을 교체하여 시스템을 완전히 폐쇄형으로 전환한다. `/v1/chat/completions` 핸들러, RAG 파이프라인, 프론트엔드는 수정하지 않는다.
