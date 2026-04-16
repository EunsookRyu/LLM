# 내부 문서 AI 챗봇 — 예시코드 가이드

> **LLM 도입 가이드 1~13장**에 대응하는 전체 예시코드의 구조, 역할, 실행 방법을 설명한다.

---

## 목차

1. [전체 프로젝트 구조](#1-전체-프로젝트-구조)
2. [아키텍처 개요](#2-아키텍처-개요)
3. [디렉토리별 상세 설명](#3-디렉토리별-상세-설명)
   - [3.1 backend/ — FastAPI 백엔드 서버](#31-backend--fastapi-백엔드-서버)
   - [3.2 frontend/ — Streamlit 프론트엔드](#32-frontend--streamlit-프론트엔드)
   - [3.3 frontend-nextchat/ — NextChat 프론트엔드](#33-frontend-nextchat--nextchat-프론트엔드)
   - [3.4 deploy/ — Docker Compose 배포](#34-deploy--docker-compose-배포)
   - [3.5 .vscode/ — 에디터 설정](#35-vscode--에디터-설정)
4. [파일별 역할 요약표](#4-파일별-역할-요약표)
5. [데이터 흐름](#5-데이터-흐름)
6. [가이드 장별 코드 매핑](#6-가이드-장별-코드-매핑)
7. [환경변수 설정 가이드](#7-환경변수-설정-가이드)
8. [실행 방법](#8-실행-방법)

---

## 1. 전체 프로젝트 구조

```
LLM 가이드 예시코드/
│
├── .vscode/                        # VS Code 에디터 설정
│   └── settings.json
│
├── backend/                        # FastAPI 백엔드 서버
│   ├── models/                     #   Pydantic 데이터 모델
│   │   ├── __init__.py
│   │   ├── chat.py                 #   채팅 요청/응답 모델
│   │   └── document.py             #   문서 관리 요청/응답 모델
│   │
│   ├── routers/                    #   API 라우터 (엔드포인트 정의)
│   │   ├── __init__.py
│   │   ├── chat.py                 #   /v1/chat/completions 엔드포인트
│   │   └── documents.py            #   /documents/* 엔드포인트
│   │
│   ├── services/                   #   비즈니스 로직 서비스 계층
│   │   ├── __init__.py
│   │   ├── llm.py                  #   LLM 호출 (CLOVA / Ollama / vLLM)
│   │   ├── embeddings.py           #   임베딩 생성 (CLOVA / 로컬 BGE-M3)
│   │   ├── conversation.py         #   대화 이력 관리
│   │   ├── vector_store.py         #   Qdrant 벡터 DB 연동
│   │   ├── document_loader.py      #   파일 텍스트 추출 (PDF/DOCX/TXT/MD)
│   │   ├── chunker.py              #   텍스트 청킹 (재귀적 분할)
│   │   ├── indexer.py              #   인덱싱 파이프라인 (추출→청킹→임베딩→저장)
│   │   ├── retriever.py            #   문서 검색 + 중복 제거
│   │   └── rag_prompt.py           #   RAG 프롬프트 구성
│   │
│   ├── auth.py                     #   API 키 인증 모듈
│   ├── config.py                   #   환경변수 설정 관리
│   ├── logger.py                   #   로깅 설정
│   ├── main.py                     #   FastAPI 앱 진입점
│   ├── requirements.txt            #   Python 의존성 목록
│   ├── Dockerfile                  #   백엔드 Docker 이미지
│   ├── .env / .env.example         #   환경변수 (로컬 개발용)
│   ├── .gitignore                  #   Git 제외 패턴
│   ├── .dockerignore               #   Docker 빌드 제외 패턴
│   ├── test_vector_store.py        #   벡터 스토어 통합 테스트
│   ├── test_indexing.py            #   인덱싱 파이프라인 테스트
│   ├── test_document.txt           #   테스트용 샘플 문서
│   ├── test_engine_comparison.py   #   CLOVA vs 로컬 엔진 비교 테스트
│   └── reindex_all.py              #   전체 재인덱싱 CLI 스크립트
│
├── frontend/                       # Streamlit 프론트엔드
│   ├── app.py                      #   채팅 UI 메인 앱
│   ├── requirements.txt            #   Python 의존성
│   ├── Dockerfile                  #   프론트엔드 Docker 이미지
│   ├── .env                        #   환경변수
│   └── .dockerignore               #   Docker 빌드 제외 패턴
│
├── frontend-nextchat/              # NextChat (Next.js) 프론트엔드 (운영 대안)
│   ├── .env.local                  #   NextChat 환경변수
│   ├── Dockerfile                  #   멀티스테이지 Docker 빌드
│   ├── .gitignore                  #   Git 제외 패턴
│   └── .dockerignore               #   Docker 빌드 제외 패턴
│
├── deploy/                         # Docker Compose 배포 설정
│   ├── docker-compose.yml          #   기본 5-서비스 구성
│   ├── docker-compose.dev.yml      #   개발 환경 오버라이드 (핫 리로드)
│   ├── docker-compose.prod.yml     #   운영 환경 오버라이드 (포트 제한)
│   ├── .env / .env.example         #   Docker Compose 환경변수
│   │
│   ├── embedding-server/           #   로컬 임베딩 서버 (BGE-M3)
│   │   ├── main.py                 #     FastAPI 임베딩 API
│   │   ├── requirements.txt        #     Python 의존성
│   │   └── Dockerfile              #     Docker 이미지
│   │
│   └── scripts/                    #   운영 스크립트
│       ├── monitor.sh              #     헬스체크 + Slack 알림
│       ├── backup_qdrant.sh        #     Qdrant 자동 백업
│       └── backup_config.sh        #     설정 파일 백업
│
└── README.md                       # ← 이 문서
```

---

## 2. 아키텍처 개요

```
┌──────────────────────────────────────────────────────────────────┐
│                        chatbot-network                           │
│                                                                  │
│  ┌───────────────┐      ┌───────────────┐      ┌──────────────┐ │
│  │   Frontend     │      │   Backend     │      │   Qdrant     │ │
│  │  (Streamlit)   │─────▶│  (FastAPI)    │─────▶│ (벡터 DB)    │ │
│  │  :8501         │      │  :8000        │      │ :6333        │ │
│  └───────────────┘      └───────┬───────┘      └──────────────┘ │
│                                 │                                │
│  ┌───────────────┐              │              ┌──────────────┐  │
│  │  NextChat      │              ├─────────────▶│   Ollama     │  │
│  │ (운영 대안)    │──────────────┘              │ (로컬 LLM)  │  │
│  │  :3000         │                             │ :11434       │  │
│  └───────────────┘                              └──────────────┘  │
│                                                                   │
│                                                ┌──────────────┐   │
│                                                │  Embedding   │   │
│                                                │   Server     │   │
│                                                │ (BGE-M3)     │   │
│                                                │ :8001        │   │
│                                                └──────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

### 서비스 구성 (5개 컨테이너)

| 서비스 | 컨테이너명 | 포트 | 역할 |
|--------|-----------|------|------|
| **frontend** | chatbot-frontend | 8501 | Streamlit 채팅 UI |
| **backend** | chatbot-backend | 8000 | FastAPI REST API, RAG 파이프라인 |
| **qdrant** | chatbot-qdrant | 6333, 6334 | 벡터 데이터베이스 (문서 임베딩 저장/검색) |
| **ollama** | chatbot-ollama | 11434 | 로컬 LLM 추론 서버 (3단계) |
| **embedding-server** | chatbot-embedding | 8001 | 로컬 BGE-M3 임베딩 서버 (3단계) |

### 엔진 선택 (환경변수로 전환)

| 단계 | LLM 엔진 | 임베딩 엔진 | 설명 |
|------|---------|------------|------|
| **2단계** 클라우드 | HyperCLOVA X API | HyperCLOVA X 임베딩 | 네이버 클라우드 API 사용 |
| **3단계** 온프레미스 | Ollama 또는 vLLM | 로컬 BGE-M3 서버 | 폐쇄망 내 자체 운영 |

---

## 3. 디렉토리별 상세 설명

### 3.1 backend/ — FastAPI 백엔드 서버

백엔드는 **FastAPI** 프레임워크로 구성되며, `models/` → `services/` → `routers/` 3계층 구조를 따른다.

#### 진입점과 설정

| 파일 | 역할 |
|------|------|
| **main.py** | FastAPI 앱 생성, CORS 설정, 요청 로깅 미들웨어, 라우터 등록, 헬스체크(`/health`) 엔드포인트. 헬스체크는 Qdrant·LLM·임베딩 서버 연결 상태를 실시간 확인 |
| **config.py** | `.env` 파일을 읽어 `Config` 클래스로 관리. API 키, Qdrant 접속 정보, LLM/임베딩 엔진 선택, API 인증 키 등 모든 설정을 중앙 집중화 |
| **auth.py** | `X-API-Key` 헤더 기반 API 인증. `API_KEY` 환경변수가 비어 있으면 인증을 건너뛰어 개발 환경에서 편리하게 사용 가능 |
| **logger.py** | `시간 | 레벨 | 모듈 | 메시지` 형식의 콘솔 로거 설정. Docker 환경에서 `docker logs`로 수집됨 |

#### models/ — 데이터 모델

Pydantic 모델로 API의 요청/응답 스키마를 정의한다.

| 파일 | 역할 |
|------|------|
| **chat.py** | OpenAI 호환 Chat Completions API 모델: `Message`, `ChatCompletionRequest`, `ChatCompletionResponse`, `ChatCompletionChunk`(스트리밍). 비스트리밍과 SSE 스트리밍 양쪽을 모두 지원 |
| **document.py** | 문서 관리 API 모델: `DocumentUploadResponse`(업로드 결과), `DocumentDeleteRequest/Response`(삭제), `CollectionInfoResponse`(컬렉션 상태) |

#### routers/ — API 엔드포인트

| 파일 | 엔드포인트 | 역할 |
|------|----------|------|
| **chat.py** | `POST /v1/chat/completions` | OpenAI 호환 채팅 API. 사용자 메시지로 RAG 검색 → 컨텍스트 주입 → LLM 호출. 스트리밍/비스트리밍 모두 지원 |
| **documents.py** | `POST /documents/upload` | 문서 파일 업로드 후 인덱싱 (PDF, DOCX, TXT, MD) |
| | `POST /documents/reupload` | 기존 문서를 새 버전으로 교체 (삭제 후 재인덱싱) |
| | `DELETE /documents/delete` | 특정 문서의 모든 벡터 삭제 |
| | `GET /documents/info` | Qdrant 컬렉션 상태 정보 조회 |

> 두 라우터 모두 `dependencies=[Depends(verify_api_key)]`로 API 키 인증이 적용되어 있다.

#### services/ — 비즈니스 로직

핵심 처리 로직을 담당하는 서비스 계층이다. 각 서비스는 모듈 수준에서 싱글턴 인스턴스를 생성하여 앱 전체에서 공유한다.

| 파일 | 싱글턴 인스턴스 | 역할 |
|------|---------------|------|
| **llm.py** | `llm_service` | LLM 엔진 어댑터. `LLM_PROVIDER` 값에 따라 `HyperClovaXService` 또는 `OpenAICompatibleService`(Ollama/vLLM 공용)를 자동 선택. `generate()`(비스트리밍)와 `generate_stream()`(SSE 스트리밍) 제공 |
| **embeddings.py** | `embedding_service` | 임베딩 엔진 어댑터. `EMBEDDING_PROVIDER` 값에 따라 `HyperClovaXEmbeddingService` 또는 `LocalEmbeddingService`(BGE-M3)를 자동 선택. `embed()`(단일)와 `embed_batch()`(배치) 제공 |
| **conversation.py** | *(함수)* | 대화 유틸리티. `ensure_system_prompt()`로 시스템 프롬프트 자동 삽입, `trim_messages()`로 긴 대화 이력 잘라 LLM 비용 절감 |
| **vector_store.py** | `vector_store` | Qdrant 벡터 DB 래퍼. 컬렉션 자동 생성, 문서 벡터 저장(`add_documents`), 코사인 유사도 검색(`search`), 출처별 삭제(`delete_by_source`), 컬렉션 정보 조회 |
| **document_loader.py** | `document_loader` | 파일 형식별 텍스트 추출기. PDF(PyMuPDF), DOCX(python-docx), TXT/MD(직접 읽기). 파일 경로와 바이트 입력 모두 지원 |
| **chunker.py** | `default_chunker` | 재귀적 텍스트 분할기. 단락→줄바꿈→문장부호→공백 순서로 분리하여 500자 청크 생성, 인접 청크 간 50자 오버랩 적용 |
| **indexer.py** | `indexing_pipeline` | 인덱싱 파이프라인. **텍스트 추출 → 청킹 → 임베딩 생성 → Qdrant 저장** 4단계를 자동 실행. `index_file()`(파일 경로)과 `index_bytes()`(업로드 바이트) 제공 |
| **retriever.py** | `retriever` | 문서 검색 서비스. 질문을 임베딩 → Qdrant 유사도 검색 → 점수 임계값 필터링(0.5) → 텍스트 중복 제거(80% 유사도). `format_context()`로 LLM용 문자열 포매팅 |
| **rag_prompt.py** | `rag_prompt_builder` | RAG 프롬프트 구성기. 검색된 문서를 시스템 프롬프트에 `[참고 문서]` 블록으로 주입. 할루시네이션 방지 지시사항 포함 |

#### 테스트/유틸리티

| 파일 | 역할 |
|------|------|
| **test_vector_store.py** | 벡터 스토어 통합 테스트: 임베딩 생성 → 저장 → 유사도 검색 → 필터링 검색 → 컬렉션 정보 확인 |
| **test_indexing.py** | 인덱싱 파이프라인 테스트: `test_document.txt` 인덱싱 후 질문별 검색 결과 출력 |
| **test_document.txt** | 테스트용 샘플 내부 규정 문서 (연차, 출장비, 보안, 비품). 노이즈 문장이 의도적으로 삽입되어 RAG 정확도 측정에 활용 |
| **test_engine_comparison.py** | CLOVA vs 로컬 엔진 비교: 미리 정의된 질문으로 양쪽 엔진의 응답 품질·속도를 비교하고 결과를 JSON 저장 |
| **reindex_all.py** | 전체 재인덱싱 CLI: 임베딩 모델 변경 후 기존 컬렉션을 삭제하고 `documents/` 폴더의 모든 파일을 재인덱싱 |

---

### 3.2 frontend/ — Streamlit 프론트엔드

Streamlit으로 만든 간단하고 빠르게 배포 가능한 채팅 UI이다.

| 파일 | 역할 |
|------|------|
| **app.py** | 채팅 UI 메인 앱. `st.chat_input`으로 사용자 입력을 받고, 백엔드 `/v1/chat/completions`에 SSE 스트리밍 요청을 보내 실시간으로 응답을 렌더링. `st.session_state`로 대화 이력 유지 |
| **requirements.txt** | 의존성: `streamlit`, `requests` |
| **Dockerfile** | Python 3.11 기반 이미지. 8501 포트에서 Streamlit 실행 |
| **.env** | `BACKEND_URL` 설정 (기본값: `http://localhost:8000`) |
| **.dockerignore** | Docker 빌드 시 제외할 파일 |

---

### 3.3 frontend-nextchat/ — NextChat 프론트엔드

운영 환경에서 더 풍부한 UI/UX를 제공하는 대안 프론트엔드이다. [NextChat](https://github.com/ChatGPTNextWeb/ChatGPT-Next-Web) 오픈소스를 활용하며, OpenAI 호환 API를 지원하므로 백엔드 변경 없이 연동된다.

| 파일 | 역할 |
|------|------|
| **.env.local** | NextChat 환경변수: 백엔드 URL, 모델명, 사이트 제목, API 키 입력란/잔액 조회 숨김 |
| **Dockerfile** | 멀티스테이지 Docker 빌드: 빌드 단계(npm ci + build) → 실행 단계(standalone 복사, 3000 포트) |
| **.gitignore** | `node_modules/`, `.next/`, `.env*.local` 등 제외 |
| **.dockerignore** | Docker 빌드 제외 패턴 |

> **참고**: NextChat 소스코드 자체는 포함되어 있지 않다. 실제 사용 시 NextChat 리포지토리를 클론한 뒤 위 설정 파일을 복사하여 사용한다.

---

### 3.4 deploy/ — Docker Compose 배포

모든 서비스를 Docker Compose로 오케스트레이션한다.

#### Compose 파일

| 파일 | 역할 | 사용법 |
|------|------|--------|
| **docker-compose.yml** | 기본 5-서비스 구성 (frontend, backend, qdrant, ollama, embedding-server). 헬스체크, 서비스 의존성, 볼륨 정의 포함 | `docker compose up -d` |
| **docker-compose.dev.yml** | 개발 환경 오버라이드. 소스 볼륨 마운트 + 핫 리로드 (`uvicorn --reload`, `streamlit runOnSave`) | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` |
| **docker-compose.prod.yml** | 운영 환경 오버라이드. 프론트엔드만 외부 노출, 나머지 서비스 포트 비공개 | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` |

#### 환경변수 파일

| 파일 | 역할 |
|------|------|
| **.env** | Docker Compose가 읽는 실제 환경변수. CLOVA API 키, LLM/임베딩 엔진 설정, Qdrant 설정, API 인증 키 포함 |
| **.env.example** | 환경변수 템플릿. `.env`로 복사 후 실제 값을 채워 넣음 |

#### embedding-server/ — 로컬 임베딩 서버

폐쇄망 환경(3단계)에서 HyperCLOVA X 임베딩 API 대신 사용하는 자체 임베딩 서버이다.

| 파일 | 역할 |
|------|------|
| **main.py** | FastAPI 앱. BGE-M3 모델을 SentenceTransformer로 로드하고 `/embed`(단건 임베딩), `/embed/batch`(배치 임베딩), `/health`, `/info` 엔드포인트 제공 |
| **requirements.txt** | 의존성: `fastapi`, `uvicorn`, `sentence-transformers`, `torch`, `transformers` |
| **Dockerfile** | Python 3.11 + PyTorch CPU 기반. 8001 포트에서 실행 |

#### scripts/ — 운영 스크립트

크론탭에 등록하여 자동화하는 운영 스크립트이다.

| 파일 | 역할 | 크론탭 예시 |
|------|------|-----------|
| **monitor.sh** | 주기적 헬스체크. 이상 감지 시 로그 기록 + Slack 웹훅 알림 | `*/5 * * * *` (5분마다) |
| **backup_qdrant.sh** | Qdrant 스냅샷 생성 → 다운로드 → 7일 이전 백업 삭제 | `0 3 * * *` (매일 03:00) |
| **backup_config.sh** | 설정 파일(docker-compose, requirements 등) tar.gz 압축 백업 | `0 3 * * 0` (매주 일요일 03:00) |

---

### 3.5 .vscode/ — 에디터 설정

| 파일 | 역할 |
|------|------|
| **settings.json** | Python 인터프리터 경로(`venv`), 저장 시 자동 포매팅, Black 포매터, 탭 크기 4 설정 |

---

## 4. 파일별 역할 요약표

총 **40개 파일** (빈 `__init__.py` 3개 포함)

| # | 경로 | 한줄 설명 |
|---|------|----------|
| 1 | `.vscode/settings.json` | VS Code Python 개발 환경 설정 |
| 2 | `backend/.dockerignore` | Docker 빌드 제외 패턴 |
| 3 | `backend/.env` | 로컬 개발용 환경변수 |
| 4 | `backend/.env.example` | 환경변수 템플릿 |
| 5 | `backend/.gitignore` | Git 제외 패턴 (API 키, 모델 파일, 캐시 등) |
| 6 | `backend/auth.py` | `X-API-Key` 헤더 기반 API 인증 |
| 7 | `backend/config.py` | 환경변수 중앙 관리 `Config` 클래스 |
| 8 | `backend/Dockerfile` | 백엔드 Docker 이미지 (Python 3.11 + uvicorn) |
| 9 | `backend/logger.py` | 콘솔 로거 설정 (Docker 로그 수집용) |
| 10 | `backend/main.py` | FastAPI 앱 진입점, 미들웨어, 헬스체크 |
| 11 | `backend/requirements.txt` | Python 의존성 9개 |
| 12 | `backend/reindex_all.py` | 전체 문서 재인덱싱 CLI |
| 13 | `backend/test_document.txt` | 테스트용 샘플 내부 규정 문서 |
| 14 | `backend/test_engine_comparison.py` | CLOVA vs 로컬 엔진 품질 비교 |
| 15 | `backend/test_indexing.py` | 인덱싱 파이프라인 테스트 |
| 16 | `backend/test_vector_store.py` | 벡터 스토어 통합 테스트 |
| 17 | `backend/models/__init__.py` | 패키지 초기화 |
| 18 | `backend/models/chat.py` | 채팅 요청/응답 Pydantic 모델 |
| 19 | `backend/models/document.py` | 문서 관리 요청/응답 Pydantic 모델 |
| 20 | `backend/routers/__init__.py` | 패키지 초기화 |
| 21 | `backend/routers/chat.py` | `/v1/chat/completions` 라우터 (RAG + LLM) |
| 22 | `backend/routers/documents.py` | `/documents/*` 라우터 (업로드/삭제/정보) |
| 23 | `backend/services/__init__.py` | 패키지 초기화 |
| 24 | `backend/services/llm.py` | LLM 멀티엔진 어댑터 (CLOVA / Ollama / vLLM) |
| 25 | `backend/services/embeddings.py` | 임베딩 멀티엔진 어댑터 (CLOVA / 로컬 BGE-M3) |
| 26 | `backend/services/conversation.py` | 시스템 프롬프트 삽입, 대화 이력 트리밍 |
| 27 | `backend/services/vector_store.py` | Qdrant 벡터 DB 래퍼 |
| 28 | `backend/services/document_loader.py` | 파일 → 텍스트 추출 (PDF/DOCX/TXT/MD) |
| 29 | `backend/services/chunker.py` | 재귀적 텍스트 분할 (500자, 50자 오버랩) |
| 30 | `backend/services/indexer.py` | 인덱싱 파이프라인 (추출→청킹→임베딩→저장) |
| 31 | `backend/services/retriever.py` | 유사도 검색 + 중복 제거 |
| 32 | `backend/services/rag_prompt.py` | RAG 컨텍스트 프롬프트 주입 |
| 33 | `frontend/app.py` | Streamlit 채팅 UI (SSE 스트리밍) |
| 34 | `frontend/requirements.txt` | 프론트엔드 Python 의존성 |
| 35 | `frontend/Dockerfile` | 프론트엔드 Docker 이미지 |
| 36 | `frontend/.env` | 백엔드 URL 설정 |
| 37 | `frontend/.dockerignore` | Docker 빌드 제외 패턴 |
| 38 | `frontend-nextchat/.env.local` | NextChat 환경변수 |
| 39 | `frontend-nextchat/Dockerfile` | NextChat 멀티스테이지 Docker 빌드 |
| 40 | `frontend-nextchat/.gitignore` | Git 제외 패턴 |
| 41 | `frontend-nextchat/.dockerignore` | Docker 빌드 제외 패턴 |
| 42 | `deploy/docker-compose.yml` | 기본 5-서비스 Compose 파일 |
| 43 | `deploy/docker-compose.dev.yml` | 개발 환경 오버라이드 (핫 리로드) |
| 44 | `deploy/docker-compose.prod.yml` | 운영 환경 오버라이드 (포트 제한) |
| 45 | `deploy/.env` | Docker Compose 환경변수 |
| 46 | `deploy/.env.example` | 환경변수 템플릿 |
| 47 | `deploy/embedding-server/main.py` | BGE-M3 임베딩 서버 API |
| 48 | `deploy/embedding-server/requirements.txt` | 임베딩 서버 의존성 |
| 49 | `deploy/embedding-server/Dockerfile` | 임베딩 서버 Docker 이미지 |
| 50 | `deploy/scripts/monitor.sh` | 헬스체크 + Slack 알림 |
| 51 | `deploy/scripts/backup_qdrant.sh` | Qdrant 자동 백업 |
| 52 | `deploy/scripts/backup_config.sh` | 설정 파일 백업 |

---

## 5. 데이터 흐름

### 5.1 문서 인덱싱 흐름 (문서 업로드 시)

```
사용자가 문서 업로드
       │
       ▼
  routers/documents.py        ← 파일 확장자/크기 검증
       │
       ▼
  services/document_loader.py ← PDF/DOCX/TXT 텍스트 추출
       │
       ▼
  services/chunker.py         ← 500자 단위 재귀적 분할 (50자 오버랩)
       │
       ▼
  services/embeddings.py      ← 각 청크를 1024차원 벡터로 변환
       │
       ▼
  services/vector_store.py    ← Qdrant에 벡터 + 메타데이터 저장
```

### 5.2 질문 응답 흐름 (채팅 시)

```
사용자 질문 입력
       │
       ▼
  frontend/app.py             ← POST /v1/chat/completions (SSE)
       │
       ▼
  routers/chat.py             ← 마지막 사용자 메시지 추출
       │
       ▼
  services/retriever.py       ← 질문 임베딩 → Qdrant 유사도 검색
       │                         → 점수 필터링 → 중복 제거
       ▼
  services/rag_prompt.py      ← 검색 결과를 시스템 프롬프트에 주입
       │
       ▼
  services/llm.py             ← LLM에 메시지 전달 → 응답 생성
       │                         (스트리밍: SSE 청크 단위 반환)
       ▼
  frontend/app.py             ← 실시간 응답 렌더링
```

---

## 6. 가이드 장별 코드 매핑

각 예시코드 파일이 가이드 원본(`LLM 가이드 수정본/`)의 **어느 장, 몇 번째 줄**에 해당하는지 상세 매핑한다.
가이드는 장이 진행될수록 같은 파일을 업그레이드하는 구조이므로, 예시코드는 **최종 버전**(마지막에 등장하는 가장 완성된 형태)을 기준으로 작성되었다.
하나의 파일이 여러 장에 걸쳐 진화하는 경우, 모든 등장 위치를 기록한다.

> **읽는 법**: `chapter4 L148–L257` → `chapter4_hyperclovax.md` 파일의 148~257번째 줄

---

### 1장 — 형상관리 (Git) · `chapter1_git.md` (743줄)

| 예시코드 파일 | 가이드 위치 | 설명 |
|-------------|-----------|------|
| `backend/.gitignore` | **chapter1 L421–L466** | 백엔드 .gitignore (환경변수, 가상환경, 모델 파일, 벡터 DB 등 제외) |
| `frontend-nextchat/.gitignore` | **chapter1 L470–L499** | 프론트엔드 .gitignore (node_modules, .next, .env*.local 등 제외) |

> 1장의 나머지 코드 블록(53개)은 Git 명령어 실습이며 별도 파일로 제공하지 않는다.

---

### 2장 — Docker 기초 · `chapter2_docker.md` (793줄)

코드로 제공되는 프로젝트 파일은 없다. Docker 설치·이미지·컨테이너·Compose 개념 설명 장이다.

> 2장에서 다루는 Dockerfile/docker-compose.yml 예시는 이후 4~5장에서 실제 프로젝트 파일로 구현된다.

---

### 3장 — Python 개발환경 · `chapter3_python.md` (668줄)

| 예시코드 파일 | 가이드 위치 | 설명 |
|-------------|-----------|------|
| `backend/config.py` | **chapter3 L203–L221** | Config 클래스 초기 버전 (CLOVA API 키만). 이후 7장·12장·13장에서 확장 |
| `backend/main.py` | **chapter3 L419–L446** | FastAPI 앱 골격 (CORS, /, /health). 이후 4장·8장·13장에서 확장 |
| `.vscode/settings.json` | **chapter3 L389–L399** | VS Code Python 개발 환경 (Black 포매터, 탭 크기) |
| `backend/models/chat.py` | **chapter3 L464–L489** | Pydantic 모델 초기 버전. 이후 4장에서 완성 |
| `backend/routers/chat.py` | **chapter3 L493–L504** | 라우터 골격. 이후 4장·9장에서 완성 |

---

### 4장 — HyperCLOVA X 연동 · `chapter4_hyperclovax.md` (833줄)

| 예시코드 파일 | 가이드 위치 | 설명 |
|-------------|-----------|------|
| `backend/services/llm.py` | **chapter4 L148–L257** | HyperClovaXService (generate, generate_stream). 이후 12장에서 멀티엔진으로 확장 |
| `backend/services/conversation.py` | **chapter4 L285–L335** | ensure_system_prompt(), trim_messages() 유틸리티 |
| `backend/models/chat.py` | **chapter4 L345–L427** | OpenAI 호환 전체 모델 (Request/Response/Chunk/Delta/Usage) — **최종 버전** |
| `backend/routers/chat.py` | **chapter4 L443–L593** | /v1/chat/completions 라우터 (비스트리밍+SSE 스트리밍). 이후 9장·13장에서 확장 |
| `backend/main.py` | **chapter4 L603–L640** | FastAPI 앱 + CORS + 라우터 등록. 이후 8장·13장에서 확장 |
| `backend/requirements.txt` | **chapter4 L654–L660** | 초기 의존성 (fastapi, uvicorn, httpx, dotenv, pydantic). 이후 7장·8장·12장에서 추가 |
| `backend/Dockerfile` | **chapter4 L668–L684** | 백엔드 Docker 이미지 — **최종 버전** |

---

### 5장 — 프론트엔드 + 배포 · `chapter5_streamlit_compose.md` (695줄)

| 예시코드 파일 | 가이드 위치 | 설명 |
|-------------|-----------|------|
| `frontend/app.py` | **chapter5 L30–L81** | Streamlit 채팅 UI (SSE 스트리밍 파싱) — **최종 버전** |
| `frontend/requirements.txt` | **chapter5 L95–L99** | streamlit, requests — **최종 버전** |
| `frontend/.env` | **chapter5 L105–L108** | BACKEND_URL — **최종 버전** |
| `frontend/Dockerfile` | **chapter5 L157–L173** | Streamlit Docker 이미지 — **최종 버전** |
| `frontend/.dockerignore` | **chapter5 L187–L197** | Docker 빌드 제외 패턴 — **최종 버전** |
| `frontend-nextchat/.env.local` | **chapter5 L137–L145** | NextChat 환경변수 — **최종 버전** |
| `frontend-nextchat/Dockerfile` | **chapter5 L203–L232** | NextChat 멀티스테이지 Docker 빌드 — **최종 버전** |
| `frontend-nextchat/.dockerignore` | **chapter5 L240–L247** | NextChat Docker 제외 패턴 — **최종 버전** |
| `deploy/docker-compose.yml` | **chapter5 L265–L341** | 초기 3-서비스 Compose. 이후 7장·11장에서 5-서비스로 확장 |
| `deploy/docker-compose.dev.yml` | **chapter5 L544–L560** | 개발 환경 오버라이드 (핫 리로드) — **최종 버전** |
| `deploy/.env` | **chapter5 L407–L411** | 초기 환경변수. 이후 11장·13장에서 확장 |
| `deploy/.env.example` | **chapter5 L415–L421** | 환경변수 템플릿 초기 버전. 이후 7장·11장에서 확장 |
| `backend/.dockerignore` | **chapter5 L473–L484** | 백엔드 Docker 제외 패턴 — **최종 버전** |

---

### 6장 — RAG 개념 · `chapter6_rag_concepts.md` (261줄)

코드로 제공되는 프로젝트 파일은 없다. RAG 아키텍처, 인덱싱/검색 파이프라인, 프롬프트 설계 등 이론 장이다.

---

### 7장 — 벡터 DB + 임베딩 · `chapter7_vectordb.md` (755줄)

| 예시코드 파일 | 가이드 위치 | 설명 |
|-------------|-----------|------|
| `backend/services/embeddings.py` | **chapter7 L293–L367** | HyperClovaXEmbeddingService (embed, embed_batch). 이후 12장에서 멀티엔진으로 확장 |
| `backend/services/vector_store.py` | **chapter7 L384–L547** | VectorStoreService (add, search, delete, info) — **최종 버전** |
| `backend/config.py` | **chapter7 L373–L376, L551–L556** | QDRANT_HOST/PORT/COLLECTION_NAME, EMBEDDING_VECTOR_SIZE 추가. 이후 12장·13장 확장 |
| `backend/test_vector_store.py` | **chapter7 L574–L635** | 벡터 스토어 통합 테스트 — **최종 버전** |
| `backend/requirements.txt` | **chapter7 L735–L743** | qdrant-client 추가. 이후 8장·12장에서 추가 |
| `deploy/.env.example` | **chapter7 L690–L702** | Qdrant/임베딩 설정 추가. 이후 11장에서 확장 |

---

### 8장 — 문서 처리 파이프라인 · `chapter8_indexing.md` (1035줄)

| 예시코드 파일 | 가이드 위치 | 설명 |
|-------------|-----------|------|
| `backend/services/document_loader.py` | **chapter8 L33–L235** | PDF/DOCX/TXT/MD 텍스트 추출기 — **최종 버전** |
| `backend/services/chunker.py` | **chapter8 L247–L429** | 재귀적 텍스트 분할 (500자, 50자 오버랩) — **최종 버전** |
| `backend/services/indexer.py` | **chapter8 L468–L614** | 인덱싱 파이프라인 (추출→청킹→임베딩→저장) — **최종 버전** |
| `backend/models/document.py` | **chapter8 L624–L654** | 문서 관리 Pydantic 모델 — **최종 버전** |
| `backend/routers/documents.py` | **chapter8 L658–L795** | 문서 업로드/교체/삭제/정보 API. 이후 13장에서 인증 추가 |
| `backend/main.py` | **chapter8 L799–L831** | documents 라우터 등록. 이후 13장에서 로깅+헬스체크 추가 |
| `backend/test_document.txt` | **chapter8 L839–L862** | 테스트용 샘플 내부 규정 문서 — **최종 버전** |
| `backend/test_indexing.py` | **chapter8 L866–L903** | 인덱싱 파이프라인 테스트 — **최종 버전** |
| `backend/requirements.txt` | **chapter8 L25–L29** | pymupdf, python-docx 추가. 이후 12장에서 openai 추가 |

---

### 9장 — RAG 통합 · `chapter9_rag_integration.md` (695줄)

| 예시코드 파일 | 가이드 위치 | 설명 |
|-------------|-----------|------|
| `backend/services/retriever.py` | **chapter9 L19–L152** | 유사도 검색 + 중복 제거 서비스 — **최종 버전** |
| `backend/services/rag_prompt.py` | **chapter9 L162–L257** | RAG 컨텍스트 프롬프트 주입 — **최종 버전** |
| `backend/routers/chat.py` | **chapter9 L285–L414** | RAG 검색→컨텍스트 주입→LLM 호출 통합. 이후 13장에서 인증 추가 |

---

### 10장 — 로컬 LLM 준비 · `chapter10_local_llm_prep.md` (516줄)

코드로 제공되는 프로젝트 파일은 없다. GPU 드라이버 설치, 모델 다운로드, Ollama/임베딩 모델 테스트 등 환경 구축 가이드이다.

> 10장의 28개 코드 블록은 모두 서버 설치 명령어와 테스트 스크립트로, 실행 후 따로 저장하지 않는다.

---

### 11장 — 온프레미스 서빙 · `chapter11_serving.md` (850줄)

| 예시코드 파일 | 가이드 위치 | 설명 |
|-------------|-----------|------|
| `deploy/embedding-server/main.py` | **chapter11 L332–L479** | BGE-M3 로컬 임베딩 서버 (FastAPI, encode, batch) — **최종 버전** |
| `deploy/embedding-server/requirements.txt` | **chapter11 L483–L490** | 임베딩 서버 의존성 — **최종 버전** |
| `deploy/embedding-server/Dockerfile` | **chapter11 L492–L509** | 임베딩 서버 Docker 이미지 — **최종 버전** |
| `deploy/docker-compose.yml` | **chapter11 L611–L729** | 최종 5-서비스 Compose (frontend, backend, qdrant, ollama, embedding-server). 이후 13장에서 API_KEY·로깅 추가 |
| `deploy/.env` | **chapter11 L733–L762** | 전체 환경변수 (CLOVA, Qdrant, LLM/임베딩 엔진 설정). 이후 13장에서 API_KEY 추가 |

---

### 12장 — 멀티엔진 전환 · `chapter12_engine_replacement.md` (918줄)

| 예시코드 파일 | 가이드 위치 | 설명 |
|-------------|-----------|------|
| `backend/services/llm.py` | **chapter12 L69–L272** | HyperClovaXService + OpenAICompatibleService + 팩토리 패턴 — **최종 버전** |
| `backend/services/embeddings.py` | **chapter12 L318–L495** | HyperClovaXEmbedding + LocalEmbeddingService + 팩토리 패턴 — **최종 버전** |
| `backend/config.py` | **chapter12 L276–L308** | LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL_NAME, EMBEDDING_PROVIDER, EMBEDDING_BASE_URL 추가. 이후 13장 API_KEY 추가 |
| `backend/reindex_all.py` | **chapter12 L507–L604** | 임베딩 모델 교체 후 전체 재인덱싱 CLI — **최종 버전** |
| `backend/test_engine_comparison.py` | **chapter12 L729–L824** | CLOVA vs 로컬 엔진 품질 비교 테스트 — **최종 버전** |
| `backend/requirements.txt` | **chapter12 L60–L63** | openai 패키지 추가 — **최종 버전** |

---

### 13장 — 운영 + 보안 · `chapter13_operations.md` (1087줄)

| 예시코드 파일 | 가이드 위치 | 설명 |
|-------------|-----------|------|
| `deploy/docker-compose.prod.yml` | **chapter13 L25–L51** | 운영 환경 Compose 오버라이드 (포트 제한) — **최종 버전** |
| `backend/auth.py` | **chapter13 L86–L115** | X-API-Key 헤더 인증 모듈 — **최종 버전** |
| `backend/config.py` | **chapter13 L121–L124** | API_KEY 설정 추가 — **최종 버전** (12장+13장 통합) |
| `backend/routers/chat.py` | **chapter13 L128–L139** | 인증 의존성 추가 — **최종 버전** (9장+13장 통합) |
| `backend/routers/documents.py` | **chapter13 L143–L150** | 인증 의존성 추가 — **최종 버전** (8장+13장 통합) |
| `backend/logger.py` | **chapter13 L211–L244** | 콘솔 로거 설정 — **최종 버전** |
| `backend/main.py` | **chapter13 L248–L273** (로깅 미들웨어), **L333–L401** (상세 헬스체크) | 로깅+헬스체크 추가 — **최종 버전** (8장+13장 통합) |
| `deploy/scripts/monitor.sh` | **chapter13 L405–L441** | 헬스체크 + Slack 알림 — **최종 버전** |
| `deploy/scripts/backup_qdrant.sh` | **chapter13 L575–L639** | Qdrant 자동 백업 — **최종 버전** |
| `deploy/scripts/backup_config.sh` | **chapter13 L707–L730** | 설정 파일 백업 — **최종 버전** |

---

### 파일별 전체 등장 이력 (여러 장에 걸쳐 진화하는 파일)

아래 파일들은 장이 진행되면서 점진적으로 확장된다. 예시코드는 **가장 오른쪽(최종) 버전**을 기준으로 작성되었다.

| 예시코드 파일 | 등장 장 (진화 순서) | 최종 버전 기준 |
|-------------|-------------------|-------------|
| `backend/config.py` | 3장 L203 → 7장 L373, L551 → 12장 L276 → 13장 L121 | **12장+13장 통합** |
| `backend/main.py` | 3장 L419 → 4장 L603 → 8장 L799 → 13장 L248, L333 | **8장+13장 통합** |
| `backend/services/llm.py` | 4장 L148 → 12장 L69 | **12장** |
| `backend/services/embeddings.py` | 7장 L293 → 12장 L318 | **12장** |
| `backend/models/chat.py` | 3장 L464 → 4장 L345 | **4장** |
| `backend/routers/chat.py` | 3장 L493 → 4장 L443 → 9장 L285 → 13장 L128 | **9장+13장 통합** |
| `backend/routers/documents.py` | 8장 L658 → 13장 L143 | **8장+13장 통합** |
| `backend/requirements.txt` | 4장 L654 → 7장 L735 → 8장 L25 → 12장 L60 | **12장** (누적 추가) |
| `deploy/docker-compose.yml` | 5장 L265 → 7장 L677 → 11장 L611 → 13장 L180 | **11장+13장 통합** |
| `deploy/.env` | 5장 L407 → 11장 L733 → 13장 L161 | **11장+13장 통합** |
| `deploy/.env.example` | 5장 L415 → 7장 L690 → 11장 (동일) | **7장+11장 통합** |

---

## 7. 환경변수 설정 가이드

### 7.1 백엔드 환경변수 (`backend/.env`)

로컬 개발 시 사용한다. Docker Compose 사용 시에는 `deploy/.env`가 우선한다.

```dotenv
# HyperCLOVA X API
CLOVA_API_KEY=발급받은_API_키
CLOVA_API_GATEWAY_KEY=발급받은_API_Gateway_키

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=documents
EMBEDDING_VECTOR_SIZE=1024
```

### 7.2 Docker Compose 환경변수 (`deploy/.env`)

모든 서비스에 적용되는 통합 환경변수이다.

| 변수명 | 기본값 | 설명 |
|--------|-------|------|
| `CLOVA_API_KEY` | *(빈 값)* | HyperCLOVA X API 키 |
| `CLOVA_API_GATEWAY_KEY` | *(빈 값)* | API Gateway 키 |
| `QDRANT_COLLECTION_NAME` | `documents` | Qdrant 컬렉션 이름 |
| `EMBEDDING_VECTOR_SIZE` | `1024` | 벡터 차원 수 |
| `LLM_PROVIDER` | `clova` | LLM 엔진: `clova`, `ollama`, `vllm` |
| `LLM_BASE_URL` | *(빈 값)* | Ollama/vLLM 서버 URL |
| `LLM_MODEL_NAME` | *(빈 값)* | 사용할 모델 이름 (예: `gemma3:12b`) |
| `EMBEDDING_PROVIDER` | `clova` | 임베딩 엔진: `clova`, `local` |
| `EMBEDDING_BASE_URL` | *(빈 값)* | 로컬 임베딩 서버 URL |
| `BGE_M3_PATH` | `/path/to/bge-m3` | BGE-M3 모델 디렉토리 경로 |
| `API_KEY` | *(빈 값)* | API 인증 키 (비워두면 인증 비활성화) |

### 7.3 엔진 전환 예시

**2단계 (클라우드)** — HyperCLOVA X API:
```dotenv
LLM_PROVIDER=clova
EMBEDDING_PROVIDER=clova
CLOVA_API_KEY=실제_키
CLOVA_API_GATEWAY_KEY=실제_키
```

**3단계 (온프레미스)** — Ollama + 로컬 임베딩:
```dotenv
LLM_PROVIDER=ollama
LLM_BASE_URL=http://ollama:11434
LLM_MODEL_NAME=gemma3:12b

EMBEDDING_PROVIDER=local
EMBEDDING_BASE_URL=http://embedding-server:8001
BGE_M3_PATH=/data/models/bge-m3
```

---

## 8. 실행 방법

### 8.1 Docker Compose로 전체 서비스 실행

```bash
cd deploy

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어 실제 값 입력

# 기본 실행
docker compose up -d

# 개발 환경 (핫 리로드)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# 운영 환경 (포트 제한)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 8.2 로컬 개발 (Python 직접 실행)

```bash
# 백엔드
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # .env 편집
uvicorn main:app --reload --port 8000

# 프론트엔드 (별도 터미널)
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

### 8.3 테스트 실행

```bash
cd backend

# 벡터 스토어 테스트 (Qdrant 실행 필요)
python test_vector_store.py

# 인덱싱 테스트
python test_indexing.py

# 엔진 비교 테스트
python test_engine_comparison.py

# 전체 재인덱싱
python reindex_all.py
```

### 8.4 서비스 접속

| 서비스 | URL |
|--------|-----|
| Streamlit 채팅 UI | http://localhost:8501 |
| 백엔드 API 문서 (Swagger) | http://localhost:8000/docs |
| 백엔드 헬스체크 | http://localhost:8000/health |
| Qdrant 관리 UI | http://localhost:6333/dashboard |
| NextChat UI (설정 시) | http://localhost:3000 |
---

## 9. 장별 단계적 코드 스냅샷 (`stages/`)

`stages/` 디렉터리에는 각 장 완료 시점의 코드 스냅샷이 들어 있다.
루트의 코드는 **13장 완료 후 최종 버전**이므로, 특정 장을 학습 중인 경우
해당 스냅샷을 참고하면 해당 단계까지의 코드만 확인할 수 있다.

### 스냅샷 구조

```
stages/
├── ch03/   ← Python 환경 + FastAPI 기본 설정
├── ch04/   ← HyperCLOVA X API 연동 + OpenAI 호환 /v1/chat/completions
├── ch05/   ← Streamlit 프론트엔드 + Docker Compose (3-서비스)
├── ch07/   ← Qdrant 벡터 DB + 임베딩 서비스
├── ch08/   ← 문서 인덱싱 파이프라인 (로더/청커/인덱서)
├── ch09/   ← RAG 파이프라인 통합 (검색기/프롬프트 빌더)
├── ch11/   ← BGE-M3 임베딩 서버 + Ollama (5-서비스 Compose)
├── ch12/   ← 다중 엔진 지원 (CLOVA/Ollama/vLLM)
└── ch13/   ← 보안/운영 강화 (README만 — 루트 코드가 최종 버전)
```

### 사용 방법

- 각 `stages/chXX/` 디렉터리에는 해당 장에서 **새로 추가되거나 변경된 파일만** 포함된다.
- 이전 장의 파일은 해당 스냅샷에 포함되지 않으므로, 전체 코드를 보려면 이전 스냅샷의 파일과 합쳐서 확인한다.
- 각 스냅샷의 `README.txt`에 가이드 라인 번호 참조와 파일 목록이 정리되어 있다.
- **ch13 스냅샷**은 루트 디렉터리의 최종 코드와 동일하므로 별도 파일을 포함하지 않는다.

### 장별 핵심 변화 요약

| 장 | 핵심 추가 사항 | 새 파일 수 |
|----|-------------|-----------|
| ch03 | `config.py`, `main.py` (기본 FastAPI) | 2 |
| ch04 | `llm.py`, `chat.py`, `models/chat.py` 등 (LLM 서빙) | 10 |
| ch05 | `frontend/app.py`, `docker-compose.yml` 등 (UI+배포) | 14 |
| ch07 | `embeddings.py`, `vector_store.py` (벡터 검색) | 7 |
| ch08 | `document_loader.py`, `chunker.py`, `indexer.py` (인덱싱) | 8 |
| ch09 | `retriever.py`, `rag_prompt.py`, 갱신된 `chat.py` (RAG) | 3 |
| ch11 | `embedding-server/*`, 5-서비스 Compose (인프라) | 5 |
| ch12 | 멀티엔진 `llm.py`/`embeddings.py`, `config.py` | 6 |
| ch13 | `auth.py`, `logger.py`, 운영 스크립트 (보안) | — (루트 참조) |