# 제13장. 운영 가이드 — 보안, 모니터링, 백업

## 13.1 이 장의 목표

제12장까지의 작업으로 기능적으로 완성된 폐쇄형 RAG 챗봇 시스템이 구축되었다. 이 장에서는 이 시스템을 실제 운영 환경에서 안정적으로 유지하기 위해 필요한 세 가지 영역을 다룬다.

첫 번째는 보안이다. 내부망에서만 접근 가능하도록 접근을 제한하고, API에 인증을 추가하고, 민감한 정보를 안전하게 관리한다.

두 번째는 모니터링이다. 시스템이 정상적으로 동작하는지 지속적으로 확인하고, 문제가 발생했을 때 신속하게 파악할 수 있는 체계를 갖춘다.

세 번째는 백업과 복구다. 인덱싱된 벡터 데이터와 시스템 설정을 주기적으로 백업하여 장애 상황에서 빠르게 복구할 수 있도록 준비한다.

---

## 13.2 보안 설정

### 네트워크 접근 제어

폐쇄형 시스템의 첫 번째 보안 원칙은 외부 접근을 최소화하는 것이다. 현재 `docker-compose.yml`에서 각 서비스의 포트를 호스트에 노출하고 있는데, 이는 개발 및 디버깅 편의를 위한 설정이다. 운영 환경에서는 외부에 공개할 필요가 없는 포트를 차단해야 한다.

외부에서 반드시 접근 가능해야 하는 포트는 프론트엔드 포트(8501)뿐이다. 백엔드, Qdrant, Ollama, 임베딩 서버는 Docker 내부 네트워크에서만 통신하면 된다.

운영 환경용 `docker-compose.prod.yml`에서 포트 노출 범위를 좁힌다.

```yaml
# docker-compose.prod.yml

services:

  backend:
    # 포트를 외부에 노출하지 않는다.
    # 프론트엔드가 내부 네트워크로 접근하므로 포트 포워딩이 불필요하다.
    ports: !reset []

  frontend:
    # Streamlit 프론트엔드만 외부에 노출한다.
    ports:
      - "8501:8501"

  qdrant:
    # Qdrant는 외부에 노출하지 않는다.
    ports: !reset []

  ollama:
    # Ollama는 외부에 노출하지 않는다.
    ports: !reset []

  embedding-server:
    # 임베딩 서버는 외부에 노출하지 않는다.
    ports: !reset []
```

운영 환경에서 실행한다.

```bash
cd deploy
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

서버의 방화벽 설정도 함께 적용한다. UFW를 사용하는 Ubuntu 환경에서는 다음과 같이 설정한다.

```bash
# 기본 정책: 외부 접속 차단
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH 접속 허용 (서버 관리용)
sudo ufw allow ssh

# Streamlit 프론트엔드만 허용
sudo ufw allow 8501/tcp

# 내부망 IP 대역에서의 접근을 추가로 허용할 경우 (선택 사항)
# sudo ufw allow from 192.168.1.0/24 to any port 8000

sudo ufw enable
sudo ufw status
```

### API 인증 추가

현재 백엔드 API는 인증 없이 누구나 접근할 수 있다. 내부 네트워크에서만 운영하더라도 기본적인 API 키 인증을 추가하는 것이 좋다.

FastAPI의 의존성 주입 기능을 활용하여 모든 API 요청에 간단한 토큰 인증을 적용한다.

```python
# auth.py
import secrets
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from config import config

# 요청 헤더에서 API 키를 읽는다.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    요청 헤더의 X-API-Key 값을 검증한다.
    키가 없거나 올바르지 않으면 401 응답을 반환한다.
    """
    if not config.API_KEY:
        # API 키가 설정되지 않은 경우 인증을 건너뛴다.
        # 개발 환경에서 편의를 위해 사용한다.
        return "no-auth"

    if not api_key or not secrets.compare_digest(api_key, config.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 API 키입니다.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key
```

`secrets.compare_digest`는 문자열 비교 시 타이밍 공격을 방지하는 안전한 비교 함수다. 일반적인 `==` 비교는 두 문자열이 처음 다른 문자에서 즉시 반환하므로, 응답 시간으로 올바른 키의 일부를 추측하는 공격에 취약하다.

`config.py`에 API 키 설정을 추가한다.

```python
# config.py에 추가
API_KEY: str = os.getenv("API_KEY", "")
```

라우터에 인증 의존성을 추가한다.

```python
# routers/chat.py 상단 수정
from fastapi import APIRouter, Depends
from fastapi import HTTPException  # 개별 핸들러에서 오류 반환 시 사용
from auth import verify_api_key

router = APIRouter(
    prefix="/v1",
    tags=["chat"],
    dependencies=[Depends(verify_api_key)]  # 이 라우터의 모든 엔드포인트에 인증 적용
)
```

문서 라우터에도 동일하게 적용한다.

```python
# routers/documents.py 상단 수정
router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(verify_api_key)]
)
```

헬스체크 엔드포인트(`/health`)는 인증 없이 접근 가능하도록 `main.py`에 직접 정의한 상태를 유지한다.

`.env` 파일에 API 키를 추가한다. 충분히 긴 무작위 문자열을 사용한다.

```bash
# 안전한 API 키 생성
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

```
# .env에 추가
API_KEY=생성된_키_값
```

### 프론트엔드에서 API 키 전달

프론트엔드가 백엔드에 요청을 보낼 때 API 키를 헤더에 포함해야 한다. Streamlit 프론트엔드는 환경 변수로 API 키를 관리한다.

```
# frontend/.env에 추가
BACKEND_URL=http://backend:8000
API_KEY=생성된_키_값
```

Streamlit 코드에서 `requests` 호출 시 `X-API-Key` 헤더를 포함하도록 구현한다. Docker 환경에서는 환경 변수로 관리하는 것이 더 안전하다.

`docker-compose.yml`의 프론트엔드 서비스에 API 키 환경 변수를 전달한다.

```yaml
  frontend:
    environment:
      - BACKEND_URL=http://backend:8000
      - API_KEY=${API_KEY}
```

> **프로덕션 대안 (NextChat 사용 시):** NextChat(ChatGPT-Next-Web)을 프론트엔드로 사용하는 경우, `frontend/.env.local`에 `CUSTOM_HEADERS={"X-API-Key": "생성된_키_값"}`을 설정하고, docker-compose에서 `BASE_URL=http://backend:8000`, `CUSTOM_MODELS=-all,+HyperCLOVA-X`, `CUSTOM_HEADERS={"X-API-Key":"${API_KEY}"}`를 환경 변수로 전달한다.

### 민감 정보 관리

`.env` 파일에 저장된 API 키와 비밀번호는 파일 시스템의 권한으로 보호한다.

```bash
# .env 파일을 소유자만 읽고 쓸 수 있도록 설정
chmod 600 .env

# 파일 소유자 확인
ls -la .env
```

Git에 `.env` 파일이 포함되지 않도록 `.gitignore`를 반드시 확인한다. 실수로 API 키를 커밋한 경우 키를 즉시 폐기하고 새로 발급받아야 한다. Git 이력에서 파일을 제거하는 것만으로는 이미 노출된 키를 안전하게 만들 수 없다.

---

## 13.3 로깅 시스템 구축

운영 환경에서는 로그를 통해 시스템 동작 상태를 파악하고 문제 발생 시 원인을 분석한다. Python의 `logging` 모듈을 활용하여 구조화된 로그를 남기도록 설정한다.

### 백엔드 로깅 설정

```python
# logger.py
import logging
import sys


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    애플리케이션 로거를 설정하고 반환한다.
    """
    logger = logging.getLogger("chatbot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    # 콘솔 핸들러 (Docker 로그로 수집됨)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # 로그 형식: 시간 | 레벨 | 모듈 | 메시지
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 모듈 수준 로거
logger = setup_logging()
```

`main.py`에서 요청과 응답을 로깅하는 미들웨어를 추가한다.

```python
# main.py에 추가
import time
from fastapi import Request
from logger import logger

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """모든 HTTP 요청의 처리 시간과 상태를 로깅한다."""
    start_time = time.time()

    # 헬스체크 엔드포인트는 로그에서 제외한다.
    if request.url.path in ("/health", "/"):
        return await call_next(request)

    response = await call_next(request)

    elapsed = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} "
        f"({elapsed:.3f}s)"
    )

    return response
```

채팅 라우터에서 주요 이벤트를 로깅한다.

```python
# routers/chat.py에 추가
from logger import logger

@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    last_msg = request.messages[-1].content if request.messages else ""
    logger.info(
        f"채팅 요청 | "
        f"모델: {request.model} | "
        f"스트리밍: {request.stream} | "
        f"메시지 길이: {len(last_msg)}자"
    )
    # ... 나머지 처리
```

### Docker 로그 설정

Docker Compose에서 로그 파일의 크기와 보관 기간을 설정하여 디스크가 가득 차는 것을 방지한다.

```yaml
# docker-compose.yml의 각 서비스에 추가
    logging:
      driver: "json-file"
      options:
        max-size: "50m"     # 파일당 최대 50MB
        max-file: "5"       # 최대 5개 파일 보관 (총 250MB)
```

로그를 실시간으로 확인하는 명령어들을 정리한다.

```bash
# 전체 서비스 로그 실시간 확인
cd deploy
docker compose logs -f

# 백엔드 로그만 확인 (최근 100줄)
docker compose logs --tail=100 -f backend

# 오류 로그만 필터링
docker compose logs backend 2>&1 | grep -i error

# 특정 시간 이후 로그 확인
docker compose logs --since="2026-02-23T09:00:00" backend
```

---

## 13.4 헬스체크와 알림

시스템의 이상을 빠르게 감지하기 위한 헬스체크 엔드포인트를 강화하고, 문제 발생 시 알림을 받을 수 있도록 설정한다.

### 상세 헬스체크 엔드포인트

현재 `/health` 엔드포인트는 단순히 `{"status": "healthy"}`를 반환한다. 실제 의존 서비스들의 연결 상태를 함께 확인하도록 강화한다.

```python
# main.py의 헬스체크 엔드포인트 수정
import httpx
from qdrant_client import QdrantClient
from config import config

@app.get("/health")
async def health_check():
    """
    전체 시스템의 상태를 확인한다.
    각 의존 서비스의 연결 상태를 함께 반환한다.
    """
    status = {
        "status": "healthy",
        "services": {}
    }
    all_healthy = True

    # Qdrant 연결 확인
    try:
        client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
        client.get_collections()
        status["services"]["qdrant"] = "healthy"
    except Exception as e:
        status["services"]["qdrant"] = f"unhealthy: {str(e)}"
        all_healthy = False

    # LLM 서버 연결 확인 (Ollama 또는 vLLM)
    if config.LLM_PROVIDER in ("ollama", "vllm") and config.LLM_BASE_URL:
        try:
            base = config.LLM_BASE_URL.replace("/v1", "")
            health_url = (
                f"{base}/api/tags" if config.LLM_PROVIDER == "ollama"
                else f"{base}/health"
            )
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                if response.status_code == 200:
                    status["services"]["llm_server"] = "healthy"
                else:
                    status["services"]["llm_server"] = f"unhealthy: HTTP {response.status_code}"
                    all_healthy = False
        except Exception as e:
            status["services"]["llm_server"] = f"unhealthy: {str(e)}"
            all_healthy = False
    else:
        status["services"]["llm_server"] = "clova_api (external)"

    # 임베딩 서버 연결 확인
    if config.EMBEDDING_PROVIDER == "local" and config.EMBEDDING_BASE_URL:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{config.EMBEDDING_BASE_URL}/health")
                if response.status_code == 200:
                    status["services"]["embedding_server"] = "healthy"
                else:
                    status["services"]["embedding_server"] = f"unhealthy: HTTP {response.status_code}"
                    all_healthy = False
        except Exception as e:
            status["services"]["embedding_server"] = f"unhealthy: {str(e)}"
            all_healthy = False
    else:
        status["services"]["embedding_server"] = "clova_api (external)"

    if not all_healthy:
        status["status"] = "degraded"

    return status
```

이 엔드포인트를 주기적으로 호출하는 간단한 모니터링 스크립트를 작성한다.

```bash
#!/bin/bash
# monitor.sh
# 크론탭에 등록하여 주기적으로 실행한다.

BACKEND_URL="http://localhost:8000"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL}"  # 선택 사항

response=$(curl -s -o /tmp/health_response.json -w "%{http_code}" "${BACKEND_URL}/health")
http_code=$response

if [ "$http_code" != "200" ]; then
    message="[내부 문서 AI 챗봇] 헬스체크 실패: HTTP ${http_code}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR | ${message}" >> /var/log/chatbot-monitor.log

    # Slack 웹훅이 설정된 경우 알림을 전송한다.
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
          -H "Content-Type: application/json" \
          -d "{\"text\": \"${message}\"}"
    fi
else
    status=$(cat /tmp/health_response.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))")

    if [ "$status" != "healthy" ]; then
        services=$(cat /tmp/health_response.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('services', {}))")
        message="[내부 문서 AI 챗봇] 서비스 이상 감지: ${services}"
        echo "$(date '+%Y-%m-%d %H:%M:%S') | WARN | ${message}" >> /var/log/chatbot-monitor.log

        if [ -n "$SLACK_WEBHOOK_URL" ]; then
            curl -s -X POST "$SLACK_WEBHOOK_URL" \
              -H "Content-Type: application/json" \
              -d "{\"text\": \"${message}\"}"
        fi
    fi
fi
```

크론탭에 5분마다 실행되도록 등록한다.

```bash
chmod +x monitor.sh

# 크론탭 편집
crontab -e

# 다음 줄 추가
*/5 * * * * /path/to/scripts/monitor.sh
```

---

## 13.5 성능 모니터링

시스템의 성능 지표를 추적하여 병목 구간을 파악하고 적절한 시점에 하드웨어를 증설할 수 있도록 준비한다.

### GPU 사용량 모니터링

LLM 서버가 GPU를 얼마나 사용하는지 주기적으로 확인한다.

```bash
# 실시간 GPU 사용량 확인
nvidia-smi dmon -s u -d 5

# 특정 컨테이너의 GPU 사용량 확인
nvidia-smi --query-compute-apps=pid,used_memory,name --format=csv

# GPU 온도와 전력 사용량 확인
nvidia-smi --query-gpu=temperature.gpu,power.draw,utilization.gpu,memory.used,memory.total --format=csv,noheader -l 5
```

### 응답 시간 측정

백엔드에서 각 단계의 처리 시간을 측정하여 병목 구간을 파악한다.

```python
# routers/chat.py에 시간 측정 추가
import time
from logger import logger

@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    timings = {}
    total_start = time.time()

    # RAG 검색 시간 측정
    t = time.time()
    search_results = await retriever.retrieve(query_text, top_k=5)
    timings["retrieval"] = round(time.time() - t, 3)

    # LLM 생성 시간은 스트리밍이 완료된 후 측정한다.
    # (스트리밍 방식에서는 첫 토큰까지의 시간(TTFT)을 측정)

    timings["total"] = round(time.time() - total_start, 3)

    logger.info(
        f"처리 시간 | "
        f"검색: {timings.get('retrieval', 0):.3f}s | "
        f"전체: {timings['total']:.3f}s"
    )
```

### 디스크 사용량 모니터링

벡터 데이터베이스와 모델 파일이 차지하는 디스크 공간을 주기적으로 확인한다.

```bash
# Docker 볼륨 사용량 확인
docker system df -v

# Qdrant 데이터 크기 확인
docker exec chatbot-qdrant du -sh /qdrant/storage

# Ollama 모델 파일 크기 확인
docker exec chatbot-ollama du -sh /root/.ollama/models

# 전체 Docker 디스크 사용량
docker system df
```

---

## 13.6 벡터 데이터베이스 백업

인덱싱된 벡터 데이터는 시스템에서 가장 중요한 데이터다. 문서를 다시 인덱싱하면 복구할 수 있지만, 그 과정에 시간이 든다. 정기적인 백업으로 복구 시간을 단축한다.

### Qdrant 스냅샷 생성

Qdrant는 스냅샷 기능을 내장하고 있다. 스냅샷은 컬렉션의 전체 상태를 파일로 저장한다.

**개발 환경** (포트 6333이 외부에 노출된 경우)에서는 localhost로 직접 호출한다.

```bash
# REST API로 스냅샷 생성
curl -X POST "http://localhost:6333/collections/documents/snapshots"
```

**운영 환경** (`docker-compose.prod.yml`에서 Qdrant 포트를 외부에 노출하지 않은 경우)에는 `docker exec`를 통해 컨테이너 내부에서 호출한다. 컨테이너 안에서는 localhost로 Qdrant에 접근할 수 있다.

```bash
# 운영 환경 — 컨테이너 내부에서 스냅샷 생성
docker exec chatbot-qdrant \
  curl -s -X POST "http://localhost:6333/collections/documents/snapshots"
```

응답으로 스냅샷 파일명이 반환된다.

```json
{
  "result": {
    "name": "documents-2026-02-23-09-00-00.snapshot",
    "creation_time": "2026-02-23T09:00:00",
    "size": 15728640
  }
}
```

스냅샷 파일 목록을 확인하고 내려받는다.

```bash
# 스냅샷 목록 확인
curl "http://localhost:6333/collections/documents/snapshots"

# 스냅샷 파일 다운로드
curl -o ~/backup/documents-snapshot.snapshot \
  "http://localhost:6333/collections/documents/snapshots/documents-2026-02-23-09-00-00.snapshot"
```

### 백업 자동화 스크립트

```bash
#!/bin/bash
# backup_qdrant.sh
# 크론탭에 등록하여 매일 자동으로 실행한다.

BACKUP_DIR="${HOME}/chatbot-backups/qdrant"
COLLECTION="documents"
DATE=$(date '+%Y%m%d_%H%M%S')

# 운영 환경에서는 Qdrant 포트가 외부에 노출되지 않으므로
# docker exec를 통해 컨테이너 내부에서 API를 호출한다.
# 포트가 노출된 개발 환경에서는 localhost:6333을 직접 사용한다.
if docker ps --filter "name=chatbot-qdrant" --format "{{.Names}}" | grep -q chatbot-qdrant; then
    USE_DOCKER_EXEC=true
    QDRANT_INTERNAL="http://localhost:6333"
    QDRANT_URL="http://localhost:6333"  # 파일 다운로드용 (포트 노출 여부에 따라)
else
    USE_DOCKER_EXEC=false
    QDRANT_URL="http://localhost:6333"
fi
BACKUP_FILE="${BACKUP_DIR}/${COLLECTION}_${DATE}.snapshot"
KEEP_DAYS=7   # 7일치 백업 보관

mkdir -p "${BACKUP_DIR}"

echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | Qdrant 백업 시작"

# 스냅샷 생성 (운영 환경은 docker exec 사용)
if [ "$USE_DOCKER_EXEC" = true ]; then
    snapshot_response=$(docker exec chatbot-qdrant \
      curl -s -X POST "${QDRANT_INTERNAL}/collections/${COLLECTION}/snapshots")
else
    snapshot_response=$(curl -s -X POST \
      "${QDRANT_URL}/collections/${COLLECTION}/snapshots")
fi

snapshot_name=$(echo "$snapshot_response" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['result']['name'])")

if [ -z "$snapshot_name" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR | 스냅샷 생성 실패"
    exit 1
fi

# 스냅샷 파일 다운로드
curl -s -o "${BACKUP_FILE}" \
  "${QDRANT_URL}/collections/${COLLECTION}/snapshots/${snapshot_name}"

if [ $? -eq 0 ]; then
    size=$(du -sh "${BACKUP_FILE}" | cut -f1)
    echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | 백업 완료: ${BACKUP_FILE} (${size})"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR | 백업 파일 다운로드 실패"
    exit 1
fi

# 서버에서 스냅샷 삭제 (디스크 절약)
curl -s -X DELETE \
  "${QDRANT_URL}/collections/${COLLECTION}/snapshots/${snapshot_name}" \
  > /dev/null

# 오래된 백업 삭제
find "${BACKUP_DIR}" -name "*.snapshot" -mtime "+${KEEP_DAYS}" -delete
echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | ${KEEP_DAYS}일 이전 백업 삭제 완료"
```

크론탭에 매일 새벽 2시에 실행하도록 등록한다.

```bash
chmod +x backup_qdrant.sh
crontab -e
# 다음 줄 추가
0 2 * * * /path/to/scripts/backup_qdrant.sh >> /var/log/chatbot-backup.log 2>&1
```

### 스냅샷에서 복구

백업 스냅샷으로 컬렉션을 복구하는 방법이다.

**개발 환경** (포트 6333이 외부에 노출된 경우):

```bash
# 기존 컬렉션 삭제
curl -X DELETE "http://localhost:6333/collections/documents"

# 스냅샷으로 복구 (파일을 업로드)
curl -X POST \
  "http://localhost:6333/collections/documents/snapshots/recover" \
  -H "Content-Type: multipart/form-data" \
  -F "snapshot=@${HOME}/chatbot-backups/qdrant/documents_20260223_020000.snapshot"
```

**운영 환경** (포트 미노출 상태): 스냅샷 파일을 먼저 컨테이너 안으로 복사한 뒤 컨테이너 내부에서 API를 호출한다.

```bash
SNAPSHOT="${HOME}/chatbot-backups/qdrant/documents_20260223_020000.snapshot"

# 1. 스냅샷 파일을 컨테이너 안으로 복사
docker cp "${SNAPSHOT}" chatbot-qdrant:/tmp/restore.snapshot

# 2. 컨테이너 내부에서 기존 컬렉션 삭제
docker exec chatbot-qdrant \
  curl -s -X DELETE "http://localhost:6333/collections/documents"

# 3. 컨테이너 내부에서 복구 실행
docker exec chatbot-qdrant \
  curl -s -X POST \
    "http://localhost:6333/collections/documents/snapshots/recover" \
    -H "Content-Type: multipart/form-data" \
    -F "snapshot=@/tmp/restore.snapshot"
```

복구 진행 상황은 컬렉션 정보로 확인한다.

```bash
# 개발 환경
curl "http://localhost:6333/collections/documents"

# 운영 환경
docker exec chatbot-qdrant curl -s "http://localhost:6333/collections/documents"
```

`status`가 `green`으로 변경되면 복구가 완료된 것이다.

---

## 13.7 설정 및 문서 백업

벡터 데이터 외에 시스템 설정 파일과 원본 문서도 백업한다.

### 설정 파일 백업

```bash
#!/bin/bash
# backup_config.sh

BACKUP_DIR="${HOME}/chatbot-backups/config"
DATE=$(date '+%Y%m%d_%H%M%S')

mkdir -p "${BACKUP_DIR}"

# 각 저장소의 설정 파일을 백업한다 (민감 정보가 없는 파일만 포함)
tar -czf "${BACKUP_DIR}/config_${DATE}.tar.gz" \
  --exclude='.env' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.git' \
  -C "${HOME}" \
  docker-compose.yml \
  docker-compose.prod.yml \
  .env.example \
  embedding-server/requirements.txt \
  backend/requirements.txt

echo "설정 백업 완료: ${BACKUP_DIR}/config_${DATE}.tar.gz"
```

`.env` 파일처럼 민감 정보가 담긴 파일은 별도로 암호화하여 백업한다.

```bash
# GPG로 .env 파일 암호화하여 백업
gpg --symmetric --cipher-algo AES256 -o \
  "${BACKUP_DIR}/env_${DATE}.gpg" \
  ~/.env

# 복호화
gpg -o .env "${BACKUP_DIR}/env_20260223_020000.gpg"
```

### 원본 문서 보관

인덱싱에 사용한 원본 문서 파일을 별도 폴더에 보관한다. 재인덱싱이 필요할 때 이 폴더에서 파일을 가져온다.

```bash
# 문서 백업 폴더 구조 권장 예시
backend/
└── documents/
    ├── 2026_01/
    │   ├── 업무매뉴얼_v3.pdf
    │   └── 업무_매뉴얼_2026.docx
    └── 2026_02/
        └── 업무매뉴얼_v4.pdf
```

문서를 버전별로 폴더를 나누어 보관하면 특정 시점의 문서로 재인덱싱하기 쉽다.

---

## 13.8 장애 대응 시나리오

운영 중 발생할 수 있는 주요 장애 유형과 대응 방법을 정리한다.

### 시나리오 1: 챗봇이 응답하지 않는 경우

```bash
# 1. 전체 서비스 상태 확인
cd deploy
docker compose ps

# 2. 종료된 컨테이너 확인
docker compose ps -a

# 3. 해당 서비스 로그 확인
docker compose logs --tail=50 backend

# 4. 서비스 재시작
docker compose restart backend

# 5. 모든 서비스 재시작
docker compose down && docker compose up -d
```

### 시나리오 2: LLM 서버가 응답하지 않는 경우

```bash
# Ollama 상태 확인
docker compose logs ollama

# Ollama 재시작 (모델은 볼륨에 저장되어 있으므로 다시 내려받지 않아도 됨)
docker compose restart ollama

# 모델이 로드되어 있는지 확인
curl http://localhost:11434/api/tags

# 모델이 없다면 다시 내려받기
docker exec chatbot-ollama ollama pull exaone3.5:7.8b
```

### 시나리오 3: 벡터 데이터베이스 손상

```bash
# Qdrant 로그에서 오류 확인
docker compose logs qdrant

# 컬렉션 상태 확인
curl http://localhost:6333/collections/documents

# 상태가 비정상인 경우 백업에서 복구
curl -X DELETE "http://localhost:6333/collections/documents"
curl -X POST \
  "http://localhost:6333/collections/documents/snapshots/recover" \
  -F "snapshot=@~/chatbot-backups/qdrant/최근_백업_파일.snapshot"
```

### 시나리오 4: GPU 메모리 부족으로 LLM이 중단된 경우

```bash
# GPU 메모리 사용량 확인
nvidia-smi

# 다른 프로세스가 GPU를 점유하고 있는지 확인
nvidia-smi pmon -c 1

# LLM 서버 재시작
docker compose restart ollama

# 재시작 후에도 메모리 부족 오류가 반복된다면
# max-model-len을 줄이거나 더 작은 양자화 모델로 전환을 고려한다.
```

### 시나리오 5: 디스크 공간 부족

```bash
# 디스크 사용량 상위 항목 확인
du -sh /* 2>/dev/null | sort -rh | head -20

# Docker 미사용 이미지와 볼륨 정리
docker system prune -a --volumes

# 오래된 로그 파일 정리
sudo journalctl --vacuum-time=7d

# Docker 로그 크기 확인
du -sh /var/lib/docker/containers/*/*-json.log | sort -rh | head -10
```

---

## 13.9 업데이트 절차

시스템의 각 구성 요소를 업데이트할 때의 권장 절차를 정리한다.

### 애플리케이션 코드 업데이트

각 저장소의 코드를 독립적으로 업데이트한다.

```bash
# 백엔드 코드 업데이트
cd ~/backend
git pull origin main

# 배포 저장소로 이동하여 백엔드 서비스만 재빌드
cd ~/deploy
docker compose up -d --build backend

# 프론트엔드 업데이트가 있는 경우
cd ~/frontend
git pull origin main
cd ~/deploy
docker compose up -d --build frontend

# 모든 서비스를 함께 업데이트하는 경우
docker compose up -d --build
```

### 모델 업데이트

새 버전의 LLM 모델로 교체할 때는 다음 순서를 따른다.

먼저 새 모델을 내려받는다. 기존 모델을 삭제하지 않은 상태에서 내려받아 검증한 후 전환한다.

```bash
# 새 모델 내려받기
docker exec chatbot-ollama ollama pull exaone3.5:latest

# 새 모델로 테스트
curl http://localhost:11434/v1/chat/completions \
  -d '{"model": "exaone3.5:latest", "messages": [{"role":"user","content":"테스트"}]}'

# 테스트가 만족스러우면 .env에서 모델명 변경 후 백엔드 재시작
# LLM_MODEL_NAME=exaone3.5:latest
docker compose up -d --no-deps backend

# 이전 모델 삭제 (선택 사항)
docker exec chatbot-ollama ollama rm exaone3.5:7.8b
```

임베딩 모델을 교체하는 경우에는 반드시 재인덱싱을 수행한다.

```bash
# 새 임베딩 모델 다운로드
huggingface-cli download NEW_MODEL --local-dir ~/models/new-embedding-model

# .env 파일에서 임베딩 모델 경로 변경
BGE_M3_PATH=/home/사용자명/models/new-embedding-model

# 임베딩 서버 재빌드 및 재시작
docker compose up -d --build embedding-server

# 전체 재인덱싱 실행 (필수)
docker exec -it chatbot-backend python reindex_all.py
```

### Qdrant 버전 업데이트

```bash
# docker-compose.yml에서 버전 태그 변경
# image: qdrant/qdrant:v1.9.4 → image: qdrant/qdrant:v1.10.0

# 업데이트 전 백업 먼저 실행
./scripts/backup_qdrant.sh

# 이미지 교체 및 재시작
docker compose up -d qdrant

# 업데이트 후 컬렉션 정상 여부 확인
curl http://localhost:6333/collections/documents
```

---

## 13.10 운영 체크리스트

정기적으로 확인해야 할 항목을 정리한다.

### 일간 확인 항목

```bash
# 전체 서비스 상태 확인
cd deploy
docker compose ps

# 헬스체크 엔드포인트 확인
curl http://localhost:8000/health | python3 -m json.tool

# GPU 메모리 사용량 확인
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader

# 디스크 사용량 확인
df -h /
```

### 주간 확인 항목

```bash
# 벡터 데이터베이스 백업 실행 및 확인
./scripts/backup_qdrant.sh
ls -lh ~/chatbot-backups/qdrant/

# 오래된 Docker 이미지 정리
docker image prune -f

# 로그 파일 크기 확인
docker system df
```

### 월간 확인 항목

새 버전의 모델이 출시되었는지 확인하고, 성능 향상이 있다면 업데이트를 검토한다.

Qdrant 공식 페이지에서 새 버전과 변경 사항을 확인하고, 보안 업데이트가 포함된 경우 우선적으로 업그레이드한다.

시스템 사용 통계를 분석하여 응답 시간이 느려지거나 오류율이 높아지는 추세가 있는지 확인한다.

---

## 13.11 전체 시스템 구조 최종 정리

이 가이드를 통해 구축한 시스템의 전체 구조를 마지막으로 정리한다.

### 아키텍처 개요

```
[사용자 브라우저]
    │
    │ HTTPS (운영 환경에서 nginx 또는 역방향 프록시 추가 권장)
    ▼
[프론트엔드(Streamlit) :8501]
    │
    │ HTTP (/v1/chat/completions — 내부 네트워크)
    ▼
[FastAPI 백엔드 :8000]
    ├── [Qdrant :6333]            벡터 데이터베이스
    ├── [Ollama :11434]           LLM 서버 (개발)
    ├── [vLLM :8080]              LLM 서버 (운영)
    └── [임베딩 서버 :8001]       BGE-M3 임베딩 생성 서버
```

### 최종 파일 구조 (3개 저장소)

```
backend/                 # 백엔드 API 저장소
├── .dockerignore
├── Dockerfile
├── requirements.txt
├── main.py                           진입점, 미들웨어 설정
├── config.py                         환경 변수 및 설정
├── auth.py                           API 키 인증
├── logger.py                         로깅 설정
├── reindex_all.py                    전체 재인덱싱 스크립트
├── test_engine_comparison.py         엔진 비교 테스트
├── test_vector_store.py
├── test_indexing.py
├── test_document.txt
├── documents/                        원본 내부 업무 문서 보관 폴더
├── routers/
│   ├── __init__.py
│   ├── chat.py                       /v1/chat/completions 핸들러
│   └── documents.py
├── services/
│   ├── __init__.py
│   ├── llm.py                        다중 엔진 지원 LLM 서비스
│   ├── embeddings.py                 다중 엔진 지원 임베딩 서비스
│   ├── vector_store.py               Qdrant 벡터 DB 서비스
│   ├── document_loader.py            문서 로더
│   ├── chunker.py                    텍스트 청커
│   ├── indexer.py                    인덱싱 파이프라인
│   ├── retriever.py                  검색 서비스
│   └── rag_prompt.py                 RAG 프롬프트 구성
└── models/
    ├── __init__.py
    ├── chat.py
    └── document.py

frontend/                # Streamlit 프론트엔드 저장소
├── .env                              BACKEND_URL, API_KEY 등
├── next.config.mjs
├── package.json
└── ...

deploy/                  # 배포 및 인프라 저장소
├── docker-compose.yml                5서비스: 프론트엔드(Streamlit), 백엔드, Qdrant, Ollama, 임베딩
├── docker-compose.prod.yml           운영 환경 오버라이드
├── .env                              실제 환경 변수 (gitignore)
├── .env.example                      환경 변수 템플릿
├── .gitignore
├── README.md
├── embedding-server/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
└── scripts/
    ├── backup_qdrant.sh              Qdrant 백업 스크립트
    ├── backup_config.sh              설정 백업 스크립트
    └── monitor.sh                    헬스체크 모니터링 스크립트
```

### 엔진 전환 요약표

| 구분 | 단계 | LLM_PROVIDER | EMBEDDING_PROVIDER | 재인덱싱 필요 |
|------|------|-------------|-------------------|------------|
| 1단계 | API 챗봇 | clova | clova | - |
| 2단계 | RAG 추가 | clova | clova | 최초 1회 |
| 3단계(개발) | 로컬 LLM | ollama | local | 필요 |
| 3단계(운영) | 로컬 LLM | vllm | local | 불필요* |

*vLLM과 Ollama를 같은 임베딩 모델과 함께 사용하는 경우 재인덱싱이 필요 없다.

---

## 13.12 마치며

이 가이드를 통해 처음 HyperCLOVA X API를 이용한 간단한 챗봇에서 시작하여, RAG를 추가하고, 최종적으로 외부 네트워크 의존 없는 완전한 폐쇄형 시스템까지 단계적으로 구축했다.

이 가이드에서 적용한 핵심 설계 원칙 두 가지를 다시 짚어 둔다.

**서비스 레이어 분리**가 첫 번째다. LLM 호출과 임베딩 호출을 독립 모듈로 분리했기 때문에, 엔진 교체가 환경 변수 변경만으로 이루어졌다. 처음부터 이 원칙을 지키지 않았다면 엔진 교체 시 수십 개의 파일을 수정해야 했을 것이다.

**단계적 구축**이 두 번째다. 외부 API로 빠르게 시작하여 동작하는 시스템을 먼저 확보한 후, 단계적으로 기능을 추가하고 의존성을 줄여나갔다. 처음부터 모든 것을 로컬로 구축하려 했다면 진입 장벽이 훨씬 높았을 것이다.

시스템을 구축한 이후에도 할 일은 남아 있다. 실제 운영 환경에서 사용하면서 어떤 질문 유형에서 검색이 잘 되는지, 어떤 경우에 할루시네이션이 발생하는지를 관찰하며 RAG 파이프라인을 지속적으로 개선해야 한다. 더 좋은 임베딩 모델이나 LLM이 출시되면 교체를 검토하고, 교육 자료가 갱신될 때마다 재인덱싱을 실행하는 운영 절차를 정착시켜야 한다.

이 시스템이 조직의 내부 문서와 지식을 효율적으로 활용하는 데 도움이 되기를 바란다.
