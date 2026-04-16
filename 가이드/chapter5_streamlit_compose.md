# 제5장. 프론트엔드와 Docker Compose 통합

## 5.1 이 장의 목표

제4장에서 HyperCLOVA X API를 호출하는 백엔드 서버를 완성했다. 이 장에서는 두 가지 작업을 순서대로 진행한다. 먼저 Streamlit으로 챗봇 프론트엔드를 구현하여 백엔드에 연결하고, 실제로 대화할 수 있는 환경을 구성한다. 그 다음 Docker Compose를 이용해 프론트엔드, 백엔드, 벡터 데이터베이스를 하나의 명령어로 함께 실행할 수 있도록 통합한다.

Streamlit을 사용하는 이유는 이 가이드의 학습자가 이미 Python에 익숙하기 때문이다. Python 코드 30줄 정도로 완전한 채팅 UI를 만들 수 있어, 프론트엔드 프레임워크를 별도로 학습할 필요가 없다. 프로덕션 환경에서 더 완성도 높은 UI가 필요한 경우를 위해 NextChat(ChatGPT-Next-Web)도 대안으로 소개한다.

이 장을 마치면 터미널에서 `docker compose up -d` 한 줄만 입력하면 완전히 동작하는 챗봇 서비스가 실행되는 상태가 된다.

---

## 5.2 Streamlit 프론트엔드 구현

### Streamlit을 사용하는 이유

Streamlit은 Python만으로 웹 UI를 만들 수 있는 프레임워크다. 이 가이드의 학습자는 이미 Python에 익숙하므로, JavaScript나 React 같은 프론트엔드 기술을 별도로 배우지 않고도 30여 줄의 코드로 완전한 채팅 인터페이스를 구현할 수 있다.

Streamlit의 주요 장점은 다음과 같다.

- Python 코드만으로 UI를 구성하므로 별도의 HTML/CSS/JavaScript 지식이 필요 없다.
- `st.chat_message`와 `st.chat_input` 컴포넌트로 채팅 UI를 손쉽게 구성할 수 있다.
- 백엔드와 동일한 Python 언어를 사용하므로 학습 부담이 적다.
- 내부 문서 검색, 다중 모델 선택 등 필요한 기능을 직접 확장하기 쉬운 구조다.

### 프론트엔드 코드 작성

`frontend/` 디렉터리를 생성하고 `app.py` 파일을 작성한다.

```python
# frontend/app.py
import streamlit as st
import requests
import json
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="내부 문서 AI 챗봇", page_icon="🤖")
st.title("내부 문서 AI 챗봇")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("질문을 입력하세요"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        
        response = requests.post(
            f"{BACKEND_URL}/v1/chat/completions",
            json={
                "model": "default",
                "messages": st.session_state.messages,
                "stream": True
            },
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: ") and line != "data: [DONE]":
                    data = json.loads(line[6:])
                    delta = data["choices"][0].get("delta", {})
                    if "content" in delta:
                        full_response += delta["content"]
                        placeholder.markdown(full_response + "▌")
        
        placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})
```

코드의 핵심 구조를 설명한다.

**환경 변수**: `BACKEND_URL`은 백엔드 API 서버의 주소다. 로컬 개발 시에는 `http://localhost:8000`을, Docker Compose 환경에서는 `http://backend:8000`을 사용한다.

**세션 상태**: `st.session_state.messages`에 대화 이력을 저장한다. Streamlit은 사용자 상호작용마다 스크립트를 재실행하지만, `st.session_state`를 통해 데이터를 유지할 수 있다.

**스트리밍 처리**: 백엔드의 `/v1/chat/completions` 엔드포인트에 `stream=True`로 요청하고, SSE(Server-Sent Events) 형식의 응답을 한 줄씩 읽어 실시간으로 화면에 표시한다. `placeholder.markdown()`으로 받은 텍스트를 누적하며 갱신한다.

### 의존성 파일

`frontend/requirements.txt`를 작성한다.

```
# frontend/requirements.txt
streamlit>=1.28.0
requests>=2.31.0
```

### 환경 변수 설정

`frontend/.env` 파일로 백엔드 주소를 설정한다.

```
# frontend/.env
BACKEND_URL=http://localhost:8000
```

Docker Compose 환경에서는 환경 변수를 직접 주입하므로 이 파일은 로컬 개발에서만 사용한다.

### 로컬 실행 확인

백엔드가 포트 8000에서 실행 중인 상태에서 Streamlit을 실행한다.

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 `http://localhost:8501`에 접속하면 채팅 인터페이스가 나타난다. 메시지를 입력하면 Streamlit이 `http://localhost:8000/v1/chat/completions`로 요청을 보내고, 스트리밍 응답을 실시간으로 화면에 표시한다.

### 프로덕션 대안: NextChat

프로덕션 환경에서 더 완성도 높은 채팅 UI가 필요하다면 NextChat(ChatGPT-Next-Web)을 검토할 수 있다. NextChat은 ChatGPT와 동일한 UX를 제공하는 오픈소스 채팅 프론트엔드로, 별도의 코드 작성 없이 다음 기능들을 내장으로 제공한다.

| 기능 | Streamlit (직접 구현) | NextChat (내장) |
|------|----------------------|----------------|
| 대화 목록 관리 | 직접 구현 필요 | 사이드바 자동 관리 |
| 모바일 레이아웃 | 제한적 | 반응형 디자인 기본 제공 |
| 다크 모드 | 미지원 | 자동 전환 |
| 대화 내보내기 | 직접 구현 필요 | Markdown/이미지 내보내기 내장 |

NextChat을 사용하려면 `.env.local` 파일에 다음과 같이 설정한다.

```
# frontend-nextchat/.env.local
BASE_URL=http://localhost:8000
DEFAULT_MODEL=HyperCLOVA-X
CUSTOM_MODELS=-all,+HyperCLOVA-X
NEXT_PUBLIC_SITE_TITLE=내부 문서 AI 챗봇
HIDE_USER_API_KEY=1
HIDE_BALANCE_QUERY=1
```

실행은 `npm install && npm run dev`로 하며, 포트 3000으로 접속한다. 우리 백엔드가 OpenAI 호환 API를 제공하므로 별도 수정 없이 연결된다.

---

## 5.3 프론트엔드 Dockerfile

### Streamlit Dockerfile

Streamlit 프론트엔드를 Docker 이미지로 빌드하기 위한 Dockerfile을 작성한다. Python 기반이므로 구조가 간단하다.

```dockerfile
# frontend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 파일을 먼저 복사하여 레이어 캐시를 활용한다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드를 복사한다.
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

이 Dockerfile의 핵심 포인트를 정리한다.

**베이스 이미지**: `python:3.11-slim`은 불필요한 패키지를 제외한 경량 Python 이미지다. 전체 이미지(`python:3.11`)보다 수백 MB 작다.

**레이어 캐시 활용**: `requirements.txt`를 소스 코드보다 먼저 복사하고 `pip install`을 실행한다. 의존성이 변경되지 않으면 이 레이어를 캐시에서 재사용하여 빌드 시간을 단축한다.

**`--no-cache-dir`**: pip 다운로드 캐시를 저장하지 않아 이미지 크기를 줄인다.

**Streamlit 실행 옵션**: `--server.port=8501`은 기본 포트를 명시하고, `--server.address=0.0.0.0`은 컨테이너 외부에서 접속할 수 있도록 모든 네트워크 인터페이스에 바인딩한다.

`.dockerignore` 파일로 빌드 컨텍스트에서 불필요한 파일을 제외한다.

```
# frontend/.dockerignore
__pycache__/
*.pyc
*.pyo
.venv/
venv/
.env
*.log
.git/
```

### 프로덕션 대안: NextChat Dockerfile

NextChat을 Docker로 빌드하려면 Next.js 프로젝트용 멀티스테이지 Dockerfile을 작성한다.

```dockerfile
# frontend-nextchat/Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# 의존성 파일을 먼저 복사하여 레이어 캐시를 활용한다.
COPY package.json package-lock.json ./
RUN npm ci

# 소스 코드를 복사하고 빌드한다.
COPY . .
RUN npm run build

# ─── 실행 단계 ───
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# 빌드 결과물만 복사한다.
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000

CMD ["node", "server.js"]
```

멀티스테이지 빌드를 사용하는 이유는 최종 이미지 크기를 줄이기 위해서다. 빌드 단계에서는 `node_modules`와 소스 코드가 모두 필요하지만, 실행 단계에서는 빌드 결과물만 있으면 된다. Next.js의 `standalone` 출력 모드를 사용하면 실행에 필요한 최소 파일만 추출되어 이미지 크기가 수백 MB에서 수십 MB 수준으로 줄어든다.

> **standalone 출력 모드**: `next.config.mjs`에 `output: "standalone"` 설정이 필요하다. NextChat 포크에 이 설정이 없다면 직접 추가한다.

NextChat용 `.dockerignore`는 다음과 같다.

```
# frontend-nextchat/.dockerignore
node_modules/
.next/
.env.local
*.log
.git/
```

---

## 5.4 Docker Compose로 전체 서비스 통합

이제 프론트엔드, 백엔드, 벡터 데이터베이스를 Docker Compose로 묶는다. 전체 시스템을 하나의 `docker-compose.yml`로 정의한다.

이 프로젝트는 프론트엔드와 백엔드가 별도 저장소이므로, Docker Compose 파일은 두 저장소를 포함하는 **상위 디렉터리**에 배치하거나, 백엔드 저장소에 배치하고 프론트엔드 경로를 상대 참조한다. 여기서는 별도의 배포 디렉터리(`deploy`)를 만드는 방식을 사용한다.

```
deploy/              # 배포 설정 전용 디렉터리
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env                         # API 키 등 실제 환경 변수
└── .env.example
```

```yaml
# docker-compose.yml
services:

  # ─────────────────────────────────────────────
  # 프론트엔드 — Streamlit
  # ─────────────────────────────────────────────
  frontend:
    build:
      context: ../frontend
      dockerfile: Dockerfile
    container_name: chatbot-frontend
    ports:
      - "8501:8501"
    environment:
      - BACKEND_URL=http://backend:8000
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
    networks:
      - chatbot-network

  # ─────────────────────────────────────────────
  # 백엔드 — FastAPI
  # ─────────────────────────────────────────────
  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    container_name: chatbot-backend
    ports:
      - "8000:8000"
    environment:
      - CLOVA_API_KEY=${CLOVA_API_KEY}
      - CLOVA_API_GATEWAY_KEY=${CLOVA_API_GATEWAY_KEY}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
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

  # ─────────────────────────────────────────────
  # 벡터 데이터베이스 — Qdrant
  # ─────────────────────────────────────────────
  qdrant:
    image: qdrant/qdrant:v1.9.4
    container_name: chatbot-qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - chatbot-network

volumes:
  qdrant-data:

networks:
  chatbot-network:
    driver: bridge
```

이 구성의 핵심 포인트를 정리한다.

### 서비스 간 통신

세 서비스가 모두 `chatbot-network`에 속해 있으므로, 컨테이너 간에는 서비스 이름으로 통신할 수 있다.

| 출발 | 도착 | 주소 |
|------|------|------|
| 프론트엔드 | FastAPI | `http://backend:8000` |
| FastAPI | Qdrant | `http://qdrant:6333` |
| 브라우저(외부) | 프론트엔드 (Streamlit) | `http://localhost:8501` |
| 브라우저(외부) | 프론트엔드 (NextChat 사용 시) | `http://localhost:3000` |
| 브라우저(외부) | FastAPI Swagger | `http://localhost:8000/docs` |
| 브라우저(외부) | Qdrant Dashboard | `http://localhost:6333/dashboard` |

프론트엔드의 `BACKEND_URL` 환경 변수를 `http://backend:8000`으로 설정하면, 프론트엔드는 Docker 내부 네트워크를 통해 백엔드에 접근한다.

> **NextChat 대안 Compose 서비스**: NextChat을 사용하려면 위 `frontend` 서비스를 다음으로 교체한다.
> ```yaml
>   frontend:
>     build:
>       context: ../frontend-nextchat
>       dockerfile: Dockerfile
>     container_name: chatbot-frontend
>     ports:
>       - "3000:3000"
>     environment:
>       - BASE_URL=http://backend:8000
>       - DEFAULT_MODEL=HyperCLOVA-X
>       - CUSTOM_MODELS=-all,+HyperCLOVA-X
>       - NEXT_PUBLIC_SITE_TITLE=내부 문서 AI 챗봇
>       - HIDE_USER_API_KEY=1
>       - HIDE_BALANCE_QUERY=1
>     depends_on:
>       backend:
>         condition: service_healthy
>     restart: unless-stopped
>     networks:
>       - chatbot-network
> ```

### healthcheck와 depends_on

백엔드의 `healthcheck`는 `/health` 엔드포인트에 주기적으로 요청을 보내 서버가 정상인지 확인한다. `start_period: 10s`는 컨테이너 시작 후 10초간 헬스체크 실패를 무시하여, 서버가 완전히 기동되기 전에 비정상으로 판정되는 것을 방지한다.

`depends_on`에 `condition: service_healthy`를 설정하면, 의존 대상 서비스가 단순히 시작된 것이 아니라 헬스체크까지 통과해야 다음 서비스가 실행된다. 이 설정이 없으면 서비스 실행 순서만 보장될 뿐, 실제 준비 완료 여부는 알 수 없어 초기 연결 오류가 발생할 수 있다.

서비스 기동 순서와 의존 관계는 다음과 같다.

- **qdrant** → 헬스체크 통과 후 → **backend** 기동
- **backend** → 헬스체크 통과 후 → **frontend** 기동

백엔드가 Qdrant보다 먼저 시작되면 벡터 DB 연결 오류(`Connection refused`)가 발생하므로, `backend` 서비스에 `depends_on.qdrant`를 반드시 설정해야 한다.

### Qdrant 볼륨

`qdrant-data`라는 명명된 볼륨을 사용하여 벡터 데이터를 영속적으로 저장한다. `docker compose down`으로 서비스를 내려도 데이터는 유지된다. 볼륨까지 삭제하려면 `docker compose down -v`를 사용한다.

Qdrant는 현재 단계에서는 아직 사용하지 않지만, 다음 단계(RAG 구축)에서 바로 사용할 수 있도록 미리 포함시켜 둔다. 지금은 비어 있는 상태로 실행되며, 리소스를 거의 소비하지 않는다.

### .env 파일

Docker Compose 파일에서 `${CLOVA_API_KEY}`를 참조하고 있으므로, 같은 디렉터리의 `.env` 파일에 값이 입력되어 있어야 한다.

```
# .env
CLOVA_API_KEY=발급받은_API_키
CLOVA_API_GATEWAY_KEY=발급받은_API_Gateway_키
```

`.env.example`도 함께 관리한다.

```
# .env.example
# CLOVA Studio API 키
# https://clova.ai/studio 에서 발급
CLOVA_API_KEY=여기에_API_키를_입력하세요
CLOVA_API_GATEWAY_KEY=여기에_API_Gateway_키를_입력하세요
```

---

## 5.5 전체 서비스 실행

모든 파일이 준비되었다면 배포 디렉터리에서 다음 명령어를 실행한다.

```bash
cd deploy
docker compose up -d --build
```

`--build` 옵션은 이미지를 새로 빌드하도록 강제한다. 처음 실행하거나 코드를 수정한 경우에는 이 옵션을 함께 사용한다.

Streamlit 프론트엔드는 빌드가 빠르다. Python 의존성 설치만 필요하므로 보통 1분 이내에 완료된다. 진행 상황을 실시간으로 확인하려면 `-d` 없이 실행하거나, 별도 터미널에서 로그를 확인한다.

```bash
docker compose logs -f
```

모든 서비스가 정상적으로 시작되었는지 확인한다.

```bash
docker compose ps
```

다음과 같이 세 서비스가 모두 `running` 상태여야 한다.

```
NAME                 STATUS
chatbot-frontend     running
chatbot-backend      running (healthy)
chatbot-qdrant       running (healthy)
```

브라우저에서 `http://localhost:8501`에 접속하여 채팅 인터페이스가 정상적으로 나타나는지 확인한다. 메시지를 입력하면 HyperCLOVA X의 응답이 실시간 스트리밍으로 표시되어야 한다.

서비스를 중단하려면 다음 명령어를 실행한다.

```bash
docker compose down
```

---

## 5.6 이미지 빌드 최적화

### .dockerignore

백엔드 프로젝트에 `.dockerignore`를 작성하여 빌드 컨텍스트에서 불필요한 파일을 제외한다.

```
# backend/.dockerignore
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.venv/
venv/
.env
*.log
.git/
```

프론트엔드의 `.dockerignore`는 5.3절에서 이미 작성했다.

### 빌드 캐시 활용

Docker BuildKit의 캐시 마운트를 활용하면 의존성 설치를 빠르게 할 수 있다.

**Streamlit(pip) 캐시 마운트:**

```dockerfile
# pip 캐시를 마운트하여 의존성 설치 속도 향상 (선택 사항)
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
```

**NextChat(npm) 캐시 마운트** (NextChat을 사용하는 경우):

```dockerfile
# npm 캐시를 마운트하여 의존성 설치 속도 향상 (선택 사항)
RUN --mount=type=cache,target=/root/.npm npm ci
```

이 기능을 사용하려면 Docker BuildKit이 활성화되어 있어야 한다. Docker Desktop을 사용하고 있다면 기본적으로 활성화되어 있다.

---

## 5.7 개발 중 효율적인 작업 방법

Docker Compose로 서비스를 실행하는 환경에서 코드를 수정하고 반영하는 방법을 정리한다.

### 코드 수정 후 재빌드

코드를 수정했을 때는 해당 서비스만 재빌드하고 재시작한다. 전체 서비스를 내렸다 올릴 필요가 없다.

```bash
# 백엔드만 재빌드
docker compose up -d --build backend

# 프론트엔드만 재빌드
docker compose up -d --build frontend
```

### 로그 모니터링

오류가 발생했을 때 원인을 파악하려면 로그를 확인한다.

```bash
# 특정 서비스 로그 실시간 확인
docker compose logs -f backend

# 최근 100줄만 확인
docker compose logs --tail=100 frontend
```

### 개발 모드 — 볼륨 마운트

코드를 수정할 때마다 이미지를 재빌드하는 것은 번거롭다. 개발 중에는 소스 코드를 볼륨으로 마운트하면 이미지를 다시 빌드하지 않고도 변경 사항이 즉시 반영된다.

운영 환경의 `docker-compose.yml`은 그대로 두고, 개발 환경에서만 사용할 덮어쓰기 파일을 별도로 작성한다.

```yaml
# docker-compose.dev.yml
services:
  backend:
    build:
      context: ../backend
    volumes:
      - ../backend:/app
    command: ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

  frontend:
    build:
      context: ../frontend
    command: ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.runOnSave=true"]
    volumes:
      - ../frontend:/app
```

개발 환경에서는 두 파일을 함께 사용한다. Docker Compose는 여러 파일을 지정하면 나중 파일의 설정이 앞 파일을 덮어쓴다.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

이 방식에서 주의할 점이 있다.

- 백엔드의 `--reload` 옵션은 uvicorn이 파일 변경을 감지하여 자동으로 재시작하게 한다.
- 프론트엔드의 `--server.runOnSave=true`는 Streamlit이 파일 저장을 감지하여 자동으로 앱을 갱신하게 한다. 코드 변경 시 브라우저에서 바로 결과를 확인할 수 있다.

### 백엔드만 로컬에서 실행

프론트엔드 변경 없이 백엔드만 수정하는 경우, Docker 없이 로컬에서 직접 실행하는 것이 가장 빠르다.

```bash
cd backend
source venv/bin/activate      # Windows: .\venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8000
```

Streamlit은 `.env` 파일의 `BACKEND_URL=http://localhost:8000`을 통해 로컬 백엔드에 연결된다.

---

## 5.8 현재까지의 전체 파일 구조

이 장까지 완성된 프로젝트의 전체 구조는 다음과 같다.

```
# 세 개의 독립 디렉터리

frontend/           # Streamlit 프론트엔드 (별도 Git 저장소)
├── app.py                       # 채팅 UI 메인 코드
├── requirements.txt             # Python 의존성
├── .env                         # 환경 변수 (gitignore)
├── .dockerignore
└── Dockerfile

backend/            # FastAPI 백엔드 (별도 Git 저장소)
├── main.py
├── config.py
├── routers/
│   ├── __init__.py
│   └── chat.py                  # /v1/chat/completions
├── services/
│   ├── __init__.py
│   ├── llm.py                   # HyperCLOVA X 호출 (교체 대상)
│   └── conversation.py          # 메시지 가공 유틸리티
├── models/
│   ├── __init__.py
│   └── chat.py                  # OpenAI 호환 모델
├── .dockerignore
├── Dockerfile
├── requirements.txt
├── .env
├── .env.example
└── .gitignore

deploy/              # Docker Compose 배포 설정
├── docker-compose.yml           # 프로덕션 구성
├── docker-compose.dev.yml       # 개발 구성 (볼륨 마운트)
├── .env                         # API 키 (gitignore)
└── .env.example
```

각 저장소에서 Git 커밋을 수행한다.

```bash
# 프론트엔드
cd frontend
git add app.py requirements.txt Dockerfile .dockerignore
git commit -m "Streamlit 채팅 프론트엔드 및 Docker 빌드 설정 추가"

# 백엔드
cd backend
git add .dockerignore
git commit -m "Docker 빌드 최적화 설정 추가"

# 배포 설정
cd deploy
git init
git add docker-compose.yml docker-compose.dev.yml .env.example .gitignore
git commit -m "Docker Compose 배포 설정 초기화"
```

---

## 5.9 동작 확인 체크리스트

이 장을 마무리하기 전에 다음 항목들을 순서대로 확인한다.

`docker compose up -d --build` 실행 후 `docker compose ps`에서 세 서비스가 모두 `running` 상태인지 확인한다.

`http://localhost:8501`에 접속하면 Streamlit 채팅 인터페이스가 나타나는지 확인한다.

페이지 상단에 "내부 문서 AI 챗봇"라는 제목이 표시되는지 확인한다.

메시지를 입력하고 전송했을 때, 응답이 실시간으로 글자 단위로 출력(스트리밍)되는지 확인한다.

두 번째 메시지를 보냈을 때 이전 대화 내용을 기억하고 답변하는지 확인한다.

`http://localhost:8000/docs`에서 Swagger UI가 정상 표시되는지 확인한다.

`http://localhost:6333/dashboard`에서 Qdrant 대시보드가 나타나는지 확인한다 (아직 컬렉션은 비어 있다).

| 확인 항목 | URL / 명령 | 기대 결과 |
|-----------|------------|-----------|
| 서비스 상태 | `docker compose ps` | 3개 서비스 모두 running |
| 프론트엔드 | `http://localhost:8501` | Streamlit 채팅 인터페이스 |
| 백엔드 API | `http://localhost:8000/docs` | Swagger UI |
| Qdrant | `http://localhost:6333/dashboard` | Qdrant 대시보드 |
| 스트리밍 | 채팅 메시지 입력 | 실시간 토큰 표시 |

모든 항목이 정상적으로 동작한다면 외부 API를 이용한 기본 챗봇이 완성된 것이다.

---

## 5.10 1단계 완성 및 다음 단계 안내

지금까지의 과정을 통해 다음과 같은 시스템이 구축되었다.

- HyperCLOVA X API를 호출하는 **FastAPI 백엔드**가 OpenAI 호환 형식으로 동작한다.
- **Streamlit 프론트엔드**가 Python 기반의 채팅 UI를 제공하며, 실시간 스트리밍을 지원한다. 프로덕션 환경에서는 NextChat으로 교체하여 더 풍부한 UI를 제공할 수도 있다.
- **Qdrant 벡터 데이터베이스**가 다음 단계(RAG)를 위해 준비되어 있다.
- 세 서비스가 **Docker Compose**로 통합되어 명령어 하나로 실행·중단할 수 있다.

이 시스템에는 한 가지 한계가 있다. 현재 챗봇은 HyperCLOVA X가 학습한 데이터만을 기반으로 답변한다. 우리 조직의 교육 프로그램, 운영 매뉴얼, 내부 업무 문서 같은 내부 문서의 내용은 모델이 알지 못하므로 정확한 답변을 기대하기 어렵다.

이 문제를 해결하는 것이 다음 단계인 RAG(Retrieval-Augmented Generation) 구축이다. RAG를 도입하면 챗봇이 내부 문서를 검색하여 그 내용을 바탕으로 답변할 수 있게 된다. 2단계에서는 현재 시스템에 RAG를 추가하는 과정을 단계별로 진행한다. 백엔드와 프론트엔드의 기본 구조는 그대로 유지되며, 이미 준비해 둔 Qdrant에 문서를 색인하고 검색 기능을 백엔드에 추가하는 작업이 핵심이다.

---

이것으로 제5장의 내용을 마친다. 다음 장부터는 2단계로 넘어가 RAG의 개념을 이해하고, 벡터 데이터베이스와 임베딩 모델을 이용한 문서 검색 시스템을 구축한다.
