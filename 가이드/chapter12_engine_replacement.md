# 제12장. API 엔드포인트 교체 — 완전한 폐쇄형 시스템 완성

## 12.1 이 장의 핵심

이 장은 이 가이드 전체에서 가장 중요한 순간이다. 지금까지 9개 장에 걸쳐 준비한 모든 것이 이 장에서 하나로 모인다.

교체해야 할 파일은 단 두 개다.

- `services/llm.py` — HyperCLOVA X 호출을 로컬 LLM 서버 호출로 교체
- `services/embeddings.py` — HyperCLOVA X 임베딩 API를 로컬 임베딩 서버 호출로 교체

나머지 파일은 전혀 수정하지 않는다. `/v1/chat/completions` 핸들러, RAG 파이프라인(검색, 프롬프트 주입, 청킹, 인덱싱), Qdrant 연동, 프론트엔드 모두 그대로다. 이것이 처음부터 서비스 레이어를 분리하여 설계한 이유다.

---

## 12.2 교체 설계 원칙

교체를 진행하기 전에 설계 원칙을 다시 확인한다.

### 어댑터 패턴

두 서비스 파일의 역할은 외부 인터페이스를 내부 인터페이스로 변환하는 어댑터다. HyperCLOVA X API든, Ollama든, vLLM이든, 호출하는 쪽에서는 동일한 메서드 시그니처를 사용한다.

```python
# 이 인터페이스는 엔진이 무엇이든 변하지 않는다.
await llm_service.generate(messages)
await llm_service.generate_stream(messages)

await embedding_service.embed(text)
await embedding_service.embed_batch(texts)
```

`routers/chat.py`의 `/v1/chat/completions` 핸들러는 `llm_service.generate_stream(messages)`만 호출한다. 그 뒤에 HyperCLOVA X가 있는지 Ollama가 있는지 알 필요가 없다. 프론트엔드는 더더욱 모른다.

### 환경 변수로 엔진 전환

어떤 엔진을 사용할지를 코드가 아닌 환경 변수로 결정한다. `.env` 파일의 값 하나를 바꾸는 것만으로 엔진이 전환된다. 코드를 수정하거나 이미지를 다시 빌드할 필요가 없다.

```
# .env
LLM_PROVIDER=clova    # HyperCLOVA X 사용
LLM_PROVIDER=ollama   # 로컬 Ollama 사용
LLM_PROVIDER=vllm     # 로컬 vLLM 사용
```

---

## 12.3 LLM 서비스 교체

### OpenAI 호환 클라이언트 설치

Ollama와 vLLM 모두 OpenAI API 형식과 호환되는 엔드포인트를 제공한다. 따라서 `openai` 라이브러리를 사용하면 두 서버 모두 동일한 코드로 호출할 수 있다.

```bash
pip install openai
```

`requirements.txt`에 추가한다.

```
# requirements.txt에 추가
openai==1.35.0
```

### 새 LLM 서비스 모듈

기존 `services/llm.py`를 다음 내용으로 완전히 교체한다.

```python
# services/llm.py
"""
LLM 서비스 모듈.

환경 변수 LLM_PROVIDER의 값에 따라 사용할 엔진을 자동으로 선택한다.
  - clova: HyperCLOVA X API (기본값, 1단계와 2단계)
  - ollama: 로컬 Ollama 서버 (3단계 개발 환경)
  - vllm: 로컬 vLLM 서버 (3단계 운영 환경)

외부에서는 llm_service 객체를 임포트하여 사용한다.
엔진 전환 시 이 파일 외에 수정할 코드가 없다.
"""

import httpx
import json
from typing import AsyncGenerator
from config import config


# ─────────────────────────────────────────────
# HyperCLOVA X 엔진 (기존 코드 유지)
# ─────────────────────────────────────────────

class HyperClovaXService:
    """HyperCLOVA X API를 호출하는 서비스."""

    BASE_URL = "https://clovastudio.stream.ntruss.com/testapp/v1"
    MODEL = "HCX-003"

    def __init__(self):
        self.headers = {
            "X-NCP-CLOVASTUDIO-API-KEY": config.CLOVA_API_KEY,
            "X-NCP-APIGW-API-KEY": config.CLOVA_API_GATEWAY_KEY,
            "Content-Type": "application/json",
        }

    def _build_body(
        self,
        messages: list[dict],
        temperature: float = 0.5,
        max_tokens: int = 512,
    ) -> dict:
        return {
            "messages": messages,
            "temperature": temperature,
            "maxTokens": max_tokens,
            "topP": 0.8,
            "topK": 0,
            "repeatPenalty": 5.0,
            "stopBefore": [],
            "includeAiFilters": True,
        }

    async def generate(
        self,
        messages: list[dict],
        temperature: float = 0.5,
        max_tokens: int = 512,
    ) -> str:
        url = f"{self.BASE_URL}/chat-completions/{self.MODEL}"
        body = self._build_body(messages, temperature, max_tokens)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=self.headers, json=body)
            response.raise_for_status()
            data = response.json()

        return data["result"]["message"]["content"]

    async def generate_stream(
        self,
        messages: list[dict],
        temperature: float = 0.5,
        max_tokens: int = 512,
    ) -> AsyncGenerator[str, None]:
        url = f"{self.BASE_URL}/chat-completions/{self.MODEL}"
        body = self._build_body(messages, temperature, max_tokens)

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", url, headers=self.headers, json=body
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue


# ─────────────────────────────────────────────
# OpenAI 호환 엔진 (Ollama / vLLM 공용)
# ─────────────────────────────────────────────

class OpenAICompatibleService:
    """
    OpenAI API 형식과 호환되는 LLM 서버를 호출하는 서비스.
    Ollama와 vLLM 모두 이 클래스로 처리한다.

    base_url 파라미터로 어느 서버에 연결할지 결정한다.
    Ollama: http://ollama:11434/v1
    vLLM:   http://vllm:8000/v1
    """

    def __init__(self, base_url: str, model_name: str):
        """
        base_url: LLM 서버의 기본 URL (예: http://ollama:11434/v1)
        model_name: 사용할 모델 이름 (예: exaone3.5:7.8b)
        """
        from openai import AsyncOpenAI

        self.model_name = model_name
        # OpenAI 클라이언트를 로컬 서버에 연결한다.
        # api_key는 로컬 서버에 필요 없지만 라이브러리가 요구하므로 임의 값을 넣는다.
        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key="not-needed",
        )

    async def generate(
        self,
        messages: list[dict],
        temperature: float = 0.5,
        max_tokens: int = 512,
    ) -> str:
        """단일 응답을 생성하여 완성된 텍스트를 반환한다."""
        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        return response.choices[0].message.content

    async def generate_stream(
        self,
        messages: list[dict],
        temperature: float = 0.5,
        max_tokens: int = 512,
    ) -> AsyncGenerator[str, None]:
        """스트리밍 방식으로 응답을 생성한다."""
        stream = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


# ─────────────────────────────────────────────
# 엔진 선택 및 싱글톤 인스턴스 생성
# ─────────────────────────────────────────────

def _create_llm_service():
    """
    환경 변수 LLM_PROVIDER에 따라 적절한 LLM 서비스 인스턴스를 생성한다.
    """
    provider = config.LLM_PROVIDER.lower()

    if provider == "clova":
        print(f"[LLM] HyperCLOVA X API 사용")
        return HyperClovaXService()

    elif provider in ("ollama", "vllm"):
        base_url = config.LLM_BASE_URL
        model_name = config.LLM_MODEL_NAME

        if not base_url:
            raise ValueError(
                f"LLM_PROVIDER가 '{provider}'이면 LLM_BASE_URL을 설정해야 합니다."
            )
        if not model_name:
            raise ValueError(
                f"LLM_PROVIDER가 '{provider}'이면 LLM_MODEL_NAME을 설정해야 합니다."
            )

        print(f"[LLM] {provider.upper()} 서버 사용: {base_url} / 모델: {model_name}")
        return OpenAICompatibleService(base_url=base_url, model_name=model_name)

    else:
        raise ValueError(
            f"알 수 없는 LLM_PROVIDER 값: '{provider}'\n"
            "허용 값: clova, ollama, vllm"
        )


# 외부에서 임포트하여 사용하는 싱글톤 인스턴스
llm_service = _create_llm_service()
```

### config.py 업데이트

```python
# config.py — LLM 관련 설정 추가
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
```

---

## 12.4 임베딩 서비스 교체

### 새 임베딩 서비스 모듈

기존 `services/embeddings.py`를 다음 내용으로 완전히 교체한다.

```python
# services/embeddings.py
"""
임베딩 서비스 모듈.

환경 변수 EMBEDDING_PROVIDER의 값에 따라 사용할 엔진을 자동으로 선택한다.
  - clova: HyperCLOVA X 임베딩 API (기본값, 1단계와 2단계)
  - local: 로컬 임베딩 서버 (3단계)

외부에서는 embedding_service 객체를 임포트하여 사용한다.
엔진 전환 시 이 파일 외에 수정할 코드가 없다.
"""

import asyncio
import httpx
from config import config


# ─────────────────────────────────────────────
# HyperCLOVA X 임베딩 엔진 (기존 코드 유지)
# ─────────────────────────────────────────────

class HyperClovaXEmbeddingService:
    """HyperCLOVA X 임베딩 API를 호출하는 서비스."""

    BASE_URL = "https://clovastudio.stream.ntruss.com/testapp/v1/api-tools"
    MODEL = "clir-sts-dolphin"
    VECTOR_SIZE = 1024

    def __init__(self):
        self.headers = {
            "X-NCP-CLOVASTUDIO-API-KEY": config.CLOVA_API_KEY,
            "X-NCP-APIGW-API-KEY": config.CLOVA_API_GATEWAY_KEY,
            "Content-Type": "application/json",
        }

    async def embed(self, text: str) -> list[float]:
        url = f"{self.BASE_URL}/embedding/{self.MODEL}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url, headers=self.headers, json={"text": text}
            )
            response.raise_for_status()
            data = response.json()
        return data["result"]["embedding"]

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 10,
    ) -> list[list[float]]:
        embeddings = []
        total = len(texts)
        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = await asyncio.gather(
                *[self.embed(text) for text in batch]
            )
            embeddings.extend(batch_embeddings)
            print(f"임베딩 진행: {min(i + batch_size, total)}/{total}")
            if i + batch_size < total:
                await asyncio.sleep(0.5)
        return embeddings


# ─────────────────────────────────────────────
# 로컬 임베딩 서버 엔진
# ─────────────────────────────────────────────

class LocalEmbeddingService:
    """
    제11장에서 구축한 로컬 임베딩 서버를 호출하는 서비스.

    base_url로 임베딩 서버의 주소를 지정한다.
    Docker Compose 환경에서는 http://embedding-server:8001을 사용한다.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.VECTOR_SIZE = None  # 서버에 쿼리하여 결정
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """
        첫 호출 시 서버에서 벡터 차원을 확인한다.
        매 호출마다 실행하지 않도록 플래그를 사용한다.
        """
        if self._initialized:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/info")
            response.raise_for_status()
            data = response.json()
            self.VECTOR_SIZE = data["dimension"]
            print(
                f"[임베딩] 로컬 서버 연결 확인: {self.base_url} "
                f"(벡터 차원: {self.VECTOR_SIZE})"
            )
        self._initialized = True

    async def embed(self, text: str) -> list[float]:
        """단일 텍스트를 임베딩 벡터로 변환한다."""
        await self._ensure_initialized()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/embed",
                json={"text": text},
            )
            response.raise_for_status()
            data = response.json()

        return data["embedding"]

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 32,
    ) -> list[list[float]]:
        """
        여러 텍스트를 배치 단위로 임베딩한다.
        로컬 서버는 배치 API를 지원하므로 한 번의 요청으로 처리한다.
        """
        await self._ensure_initialized()

        all_embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/embed/batch",
                    json={"texts": batch},
                )
                response.raise_for_status()
                data = response.json()

            all_embeddings.extend(data["embeddings"])
            print(f"임베딩 진행: {min(i + batch_size, total)}/{total}")

        return all_embeddings


# ─────────────────────────────────────────────
# 엔진 선택 및 싱글톤 인스턴스 생성
# ─────────────────────────────────────────────

def _create_embedding_service():
    """
    환경 변수 EMBEDDING_PROVIDER에 따라 적절한 임베딩 서비스 인스턴스를 생성한다.
    """
    provider = config.EMBEDDING_PROVIDER.lower()

    if provider == "clova":
        print("[임베딩] HyperCLOVA X 임베딩 API 사용")
        return HyperClovaXEmbeddingService()

    elif provider == "local":
        base_url = config.EMBEDDING_BASE_URL
        if not base_url:
            raise ValueError(
                "EMBEDDING_PROVIDER가 'local'이면 EMBEDDING_BASE_URL을 설정해야 합니다."
            )
        print(f"[임베딩] 로컬 임베딩 서버 사용: {base_url}")
        return LocalEmbeddingService(base_url=base_url)

    else:
        raise ValueError(
            f"알 수 없는 EMBEDDING_PROVIDER 값: '{provider}'\n"
            "허용 값: clova, local"
        )


# 외부에서 임포트하여 사용하는 싱글톤 인스턴스
embedding_service = _create_embedding_service()
```

---

## 12.5 임베딩 교체 시 재인덱싱

임베딩 모델을 교체할 때 반드시 주의해야 할 사항이 있다. HyperCLOVA X 임베딩(`clir-sts-dolphin`)과 BGE-M3 임베딩은 서로 다른 방식으로 텍스트를 벡터로 변환한다. 두 모델이 같은 차원(1024)의 벡터를 생성하더라도, 벡터 공간 자체가 다르기 때문에 한 모델로 저장한 벡터를 다른 모델로 검색하면 의미 있는 결과를 얻을 수 없다.

따라서 임베딩 모델을 교체할 때는 Qdrant `documents` 컬렉션에 인덱싱된 모든 문서를 새 모델로 다시 인덱싱해야 한다.

재인덱싱을 수행하는 스크립트를 작성한다.

```python
# reindex_all.py
"""
임베딩 모델 교체 후 모든 문서를 재인덱싱하는 스크립트.

실행 전 확인사항:
1. EMBEDDING_PROVIDER가 새 모델로 변경되어 있는지 확인한다.
2. 기존 내부 업무 문서 파일이 모두 보관되어 있는지 확인한다.
3. Qdrant와 임베딩 서버가 실행 중인지 확인한다.

주의: 이 스크립트를 실행하면 documents 컬렉션의 기존 벡터 데이터가
      모두 삭제된다.
"""

import asyncio
import sys
from pathlib import Path

from services.vector_store import vector_store
from services.indexer import indexing_pipeline


DOCUMENTS_DIR = Path("./documents")  # 재인덱싱할 문서가 저장된 폴더


async def reindex_all():
    print("=" * 60)
    print("documents 컬렉션 전체 재인덱싱 시작")
    print("=" * 60)

    # 문서 폴더 확인
    if not DOCUMENTS_DIR.exists():
        print(f"오류: 문서 폴더를 찾을 수 없습니다: {DOCUMENTS_DIR}")
        print("내부 업무 문서가 저장된 폴더 경로를 DOCUMENTS_DIR에 설정하세요.")
        sys.exit(1)

    document_files = list(DOCUMENTS_DIR.glob("**/*"))
    document_files = [
        f for f in document_files
        if f.is_file() and f.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}
    ]

    if not document_files:
        print("인덱싱할 문서 파일이 없습니다.")
        sys.exit(0)

    print(f"발견된 문서: {len(document_files)}개")
    for f in document_files:
        print(f"  - {f.name}")

    # 사용자 확인
    print("\n경고: documents 컬렉션의 모든 벡터 데이터가 삭제됩니다.")
    confirm = input("계속 진행하려면 'yes'를 입력하세요: ")
    if confirm.strip().lower() != "yes":
        print("취소되었습니다.")
        sys.exit(0)

    # 기존 컬렉션 데이터 삭제
    print("\n기존 컬렉션 데이터 삭제 중...")
    client = vector_store.client
    collection_name = vector_store.collection_name
    client.delete_collection(collection_name)
    vector_store._ensure_collection()
    print("컬렉션 초기화 완료")

    # 모든 문서 재인덱싱
    results = []
    failed = []

    for i, file_path in enumerate(document_files):
        print(f"\n[{i + 1}/{len(document_files)}] {file_path.name}")
        try:
            result = await indexing_pipeline.index_file(file_path)
            results.append(result)
        except Exception as e:
            print(f"  오류 발생: {str(e)}")
            failed.append({"file": file_path.name, "error": str(e)})

    # 결과 요약
    print("\n" + "=" * 60)
    print("재인덱싱 완료")
    print("=" * 60)
    print(f"성공: {len(results)}개 파일")
    total_chunks = sum(r["chunks"] for r in results)
    print(f"총 저장된 벡터: {total_chunks}개")

    if failed:
        print(f"\n실패: {len(failed)}개 파일")
        for f in failed:
            print(f"  - {f['file']}: {f['error']}")

    info = vector_store.get_collection_info()
    print(f"\n최종 컬렉션 상태: {info['points_count']}개 벡터 저장됨")


if __name__ == "__main__":
    asyncio.run(reindex_all())
```

---

## 12.6 엔진 전환 절차

HyperCLOVA X에서 로컬 LLM으로 전환하는 전체 절차를 단계별로 정리한다.

### 1단계: 로컬 서버 준비 확인

전환 전에 로컬 서버들이 정상 동작하는지 확인한다.

```bash
# Ollama API 응답 확인
curl http://localhost:11434/v1/models

# 임베딩 서버 응답 확인
curl http://localhost:8001/health
```

### 2단계: .env 파일 수정

`.env` 파일에서 다음 값을 변경한다. 기존 값은 주석으로 남겨두어 되돌리기 쉽게 한다.

```
# .env

# HyperCLOVA X API (이제 사용하지 않음)
CLOVA_API_KEY=기존_API_키
CLOVA_API_GATEWAY_KEY=기존_Gateway_키

# LLM 서버 설정
# LLM_PROVIDER=clova                   # 기존 설정 (주석 처리)
LLM_PROVIDER=ollama                     # 로컬 Ollama 사용
LLM_BASE_URL=http://ollama:11434/v1    # Docker Compose 내부 주소
LLM_MODEL_NAME=exaone3.5:7.8b

# 임베딩 서버 설정
# EMBEDDING_PROVIDER=clova              # 기존 설정 (주석 처리)
EMBEDDING_PROVIDER=local                # 로컬 임베딩 서버 사용
EMBEDDING_BASE_URL=http://embedding-server:8001
```

### 3단계: 백엔드 재시작

백엔드 컨테이너만 재시작한다. 이미지를 다시 빌드할 필요 없이 환경 변수만 다시 읽으면 된다.

```bash
cd deploy
docker compose up -d --no-deps backend
```

백엔드 로그에서 다음 메시지를 확인한다.

```
[LLM] OLLAMA 서버 사용: http://ollama:11434/v1 / 모델: exaone3.5:7.8b
[임베딩] 로컬 임베딩 서버 사용: http://embedding-server:8001
```

이 메시지가 나타나면 엔진이 성공적으로 전환된 것이다.

### 4단계: 기존 문서 재인덱싱

임베딩 모델이 변경되었으므로 기존 문서를 재인덱싱한다.

```bash
# 백엔드 컨테이너 안에서 재인덱싱 스크립트 실행
docker exec -it chatbot-backend python reindex_all.py
```

재인덱싱이 완료되면 Qdrant 대시보드(`http://localhost:6333/dashboard`)에서 `documents` 컬렉션의 포인트 수가 동일하게 복원되었는지 확인한다.

### 5단계: 프론트엔드에서 동작 확인

브라우저에서 `http://localhost:8501`에 접속하여 Streamlit 챗봇이 정상적으로 응답하는지 확인한다. 이전과 동일한 방식으로 대화할 수 있으면 전환이 완료된 것이다. 프론트엔드는 백엔드 엔진 전환을 전혀 인지하지 못한다.

---

## 12.7 vLLM으로 전환

Ollama에서 vLLM으로 전환하는 절차는 더욱 간단하다. vLLM도 OpenAI 호환 API를 사용하기 때문에 `OpenAICompatibleService` 클래스를 그대로 사용한다.

`.env` 파일의 두 줄만 변경한다.

```
# Ollama → vLLM 전환
LLM_PROVIDER=vllm
LLM_BASE_URL=http://vllm:8000/v1      # vLLM 서버 내부 주소
LLM_MODEL_NAME=exaone                  # vLLM에서 설정한 served-model-name
```

백엔드를 재시작한다.

```bash
docker compose up -d --no-deps backend
```

임베딩 모델은 변경되지 않으므로 재인덱싱이 필요 없다. 프론트엔드에서 질문을 입력하여 vLLM에서 응답이 생성되는지 확인한다.

---

## 12.8 HyperCLOVA X로 되돌리기

로컬 LLM에 문제가 생겼거나 일시적으로 API로 되돌려야 할 때는 `.env` 파일의 두 줄을 원래대로 변경하면 된다.

```
LLM_PROVIDER=clova
EMBEDDING_PROVIDER=clova
```

백엔드를 재시작하고, 임베딩 모델이 다시 HyperCLOVA X로 변경되었으므로 문서를 재인덱싱한다.

```bash
docker compose up -d --no-deps backend
docker exec -it chatbot-backend python reindex_all.py
```

이 유연성이 처음부터 서비스 레이어를 분리한 이유다. 엔진 전환이 코드 한 줄도 건드리지 않고 환경 변수 변경만으로 이루어진다.

---

## 12.9 전환 후 품질 비교 테스트

엔진 전환 후 품질이 기대 수준인지 확인하는 체계적인 테스트를 권장한다.

```python
# test_engine_comparison.py
"""
두 엔진의 응답 품질을 비교하는 테스트 스크립트.
먼저 CLOVA 엔진으로 실행하고, 이후 LOCAL 엔진으로 전환 후 다시 실행하여
결과를 비교한다.
"""

import asyncio
import json
from datetime import datetime

from services.llm import llm_service
from services.embeddings import embedding_service
from services.vector_store import vector_store
from config import config


TEST_QUERIES = [
    "연차 휴가 신청 절차가 어떻게 되나요?",
    "출장비 정산 방법을 알려주세요.",
    "재택근무 신청 방법을 알려주세요.",
    "사내 카페에서 외부 음식을 먹을 수 있나요?",       # 문서에 없는 질문 (할루시네이션 테스트)
]


async def run_test():
    print(f"테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"LLM 엔진: {config.LLM_PROVIDER}")
    print(f"임베딩 엔진: {config.EMBEDDING_PROVIDER}")
    print("=" * 60)

    results = []

    for query in TEST_QUERIES:
        print(f"\n질문: {query}")

        # 임베딩 및 검색
        query_embedding = await embedding_service.embed(query)
        search_results = vector_store.search(query_embedding, top_k=3)

        context_parts = []
        for r in search_results:
            source = r.get("source", "")
            text = r["text"]
            context_parts.append(
                f"출처: {source}\n내용: {text}"
            )
        context = "\n\n".join(context_parts)

        # LLM 응답 생성
        messages = [
            {
                "role": "system",
                "content": (
                    "당신은 조직의 내부 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다. "
                    "주어진 참고 문서를 바탕으로 질문에 답변하세요. "
                    "문서에 없는 내용은 모른다고 답변하세요."
                )
            },
            {
                "role": "user",
                "content": (
                    f"참고 문서:\n{context}\n\n질문: {query}"
                    if context else query
                )
            }
        ]

        start_time = asyncio.get_event_loop().time()
        answer = await llm_service.generate(messages, max_tokens=300)
        elapsed = asyncio.get_event_loop().time() - start_time

        print(f"응답 시간: {elapsed:.2f}초")
        print(f"답변: {answer[:200]}{'...' if len(answer) > 200 else ''}")

        results.append({
            "query": query,
            "answer": answer,
            "elapsed": round(elapsed, 2),
            "search_count": len(search_results),
        })

    # 결과 저장
    output_file = f"test_results_{config.LLM_PROVIDER}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장: {output_file}")
    avg_time = sum(r["elapsed"] for r in results) / len(results)
    print(f"평균 응답 시간: {avg_time:.2f}초")


if __name__ == "__main__":
    asyncio.run(run_test())
```

HyperCLOVA X 엔진으로 먼저 테스트를 실행하고, 로컬 엔진으로 전환한 후 다시 실행하여 두 결과 파일을 비교한다. 응답 시간, 답변의 정확성, 할루시네이션 발생 여부를 중점적으로 확인한다.

---

## 12.10 전체 파일 구조 최종 정리

```
backend/
├── .dockerignore
├── Dockerfile
├── requirements.txt
├── main.py
├── config.py                        # LLM/임베딩 프로바이더 설정 추가
├── reindex_all.py                   # 재인덱싱 스크립트
├── test_engine_comparison.py        # 엔진 비교 테스트
├── test_vector_store.py
├── test_indexing.py
├── test_document.txt
├── documents/                       # 재인덱싱용 내부 업무 문서 보관
├── routers/
│   ├── __init__.py
│   ├── chat.py                      # /v1/chat/completions (변경 없음)
│   └── documents.py
├── services/
│   ├── __init__.py
│   ├── llm.py                       # 교체 완료 (다중 엔진 지원)
│   ├── embeddings.py                # 교체 완료 (다중 엔진 지원)
│   ├── vector_store.py
│   ├── document_loader.py
│   ├── chunker.py
│   ├── indexer.py
│   ├── retriever.py
│   └── rag_prompt.py
└── models/
    ├── __init__.py
    ├── chat.py
    └── document.py

frontend/               # 별도 저장소 (변경 없음)
├── .env
└── ...


├── docker-compose.yml               # 5서비스: 프론트엔드(Streamlit), 백엔드, Qdrant, Ollama, 임베딩
├── .env                             # LLM_PROVIDER, EMBEDDING_PROVIDER
├── .gitignore
└── embedding-server/
    ├── Dockerfile
    ├── requirements.txt
    └── main.py
```

변경 사항을 커밋한다.

```bash
# backend 저장소
git add .
git commit -m "feat: 다중 엔진 지원 LLM/임베딩 서비스 교체

- services/llm.py: HyperCLOVA X / Ollama / vLLM 자동 전환
- services/embeddings.py: HyperCLOVA X / BGE-M3 로컬 자동 전환
- config.py: LLM_PROVIDER, EMBEDDING_PROVIDER 환경 변수 추가
- reindex_all.py: 임베딩 모델 교체 시 전체 재인덱싱 스크립트
- /v1/chat/completions, RAG, 프론트엔드: 변경 없음"
```

---

## 12.11 3단계 완성 — 완전한 폐쇄형 시스템

이 장까지의 작업으로 완전한 폐쇄형 RAG 챗봇이 완성되었다. 지금 구축된 시스템은 다음과 같이 동작한다.

사용자가 프론트엔드에서 질문을 입력하면, 프론트엔드는 `/v1/chat/completions`에 표준 OpenAI 형식으로 요청을 보낸다. 백엔드는 마지막 사용자 메시지를 로컬 임베딩 서버(BGE-M3)에 전달하여 벡터로 변환하고, Qdrant `documents` 컬렉션에서 관련 교육 자료를 검색한다. 검색 결과를 시스템 프롬프트에 주입한 뒤 로컬 LLM 서버(Ollama/vLLM의 EXAONE 3.5)에 전달하면, 교육 자료를 근거로 한 답변이 SSE 스트리밍으로 프론트엔드에 반환된다. 이 모든 과정에서 외부 네트워크 요청은 단 한 건도 발생하지 않는다.

서비스 간 역할과 통신 경로를 정리하면 다음과 같다.

```
[사용자 브라우저]
    ↕ HTTP
[프론트엔드(Streamlit) :8501]
    ↕ HTTP (/v1/chat/completions)
[FastAPI 백엔드 :8000]
    ↕ HTTP         ↕ HTTP                  ↕ HTTP
[Qdrant :6333] [Ollama/vLLM :11434/8080] [임베딩 서버 :8001]
```

모든 서비스가 Docker 컨테이너로 실행되며, `chatbot-network` 안에서 서비스 이름으로 서로 통신한다. 외부에서는 프론트엔드 포트(8501)와 필요에 따라 백엔드 포트(8000, Swagger UI)만 접근 가능하다. LLM 서버, 임베딩 서버, Qdrant는 외부 접근이 차단된 상태로 운영된다.

엔진 전환이 필요할 때는 `.env` 파일의 `LLM_PROVIDER`와 `EMBEDDING_PROVIDER` 값을 변경하고 백엔드를 재시작하면 된다. 코드를 수정하거나 이미지를 다시 빌드할 필요가 없다.

---

이것으로 제12장의 내용을 마친다. 이 가이드의 핵심 목표였던 완전한 폐쇄형 LLM 시스템이 완성되었다. 다음 장에서는 이 시스템을 안정적으로 운영하기 위한 보안 설정, 모니터링, 백업 방안을 다룬다.
