# 제9장. RAG 검색 및 생성 파이프라인 — 챗봇 완성

## 9.1 이 장의 목표

제8장까지의 작업으로 문서를 인덱싱하는 파이프라인이 완성되었다. 이 장에서는 나머지 절반인 검색 및 생성 파이프라인을 구현하여 챗봇과 연결한다.

구체적으로는 다음 순서로 진행한다. 먼저 사용자의 질문으로 관련 문서를 검색하는 검색 서비스를 구현한다. 이어서 검색 결과를 LLM 프롬프트에 포함시키는 RAG 프롬프트 구성 로직을 작성한다. 그 다음 기존 `/v1/chat/completions` 엔드포인트를 RAG를 지원하도록 확장한다.

핵심 설계 원칙은 **프론트엔드에 대한 투명성**이다. 프론트엔드는 표준 OpenAI 형식으로 요청을 보내고, 백엔드가 내부적으로 RAG 검색을 수행하여 컨텍스트를 주입한다. 프론트엔드 쪽 코드는 한 줄도 수정하지 않는다.

이 장을 마치면 업로드한 내부 업무 문서를 근거로 답변하는 완전한 RAG 챗봇이 완성된다.

---

## 9.2 검색 서비스 구현

사용자의 질문을 받아 관련 문서를 검색하는 로직을 `services/retriever.py`로 구현한다. 단순한 유사도 검색을 기본으로 하되, 검색 품질을 높이는 몇 가지 기법을 함께 적용한다.

```python
# services/retriever.py
from services.embeddings import embedding_service
from services.vector_store import vector_store


class RetrieverService:
    """
    사용자 질문에 관련된 문서를 Qdrant에서 검색하는 서비스.
    """

    def __init__(
        self,
        top_k: int = 5,
        score_threshold: float = 0.5,
    ):
        """
        top_k: 검색 결과로 반환할 최대 문서 수
        score_threshold: 이 점수 미만의 결과는 관련성이 낮다고 판단하여 제외
        """
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.embedding_svc = embedding_service
        self.vector_svc = vector_store

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_conditions: dict | None = None,
    ) -> list[dict]:
        """
        질문과 관련된 문서를 검색하여 반환한다.

        반환값은 유사도 점수 내림차순으로 정렬된 문서 목록이다.
        score_threshold 미만의 결과는 제외된다.
        """
        k = top_k or self.top_k

        # 1. 질문을 임베딩 벡터로 변환한다.
        query_embedding = await self.embedding_svc.embed(query)

        # 2. Qdrant에서 유사한 문서를 검색한다.
        results = self.vector_svc.search(
            query_embedding=query_embedding,
            top_k=k,
            filter_conditions=filter_conditions,
        )

        # 3. 유사도 점수가 임계값 미만인 결과를 제거한다.
        filtered = [r for r in results if r["score"] >= self.score_threshold]

        return filtered

    async def retrieve_with_dedup(
        self,
        query: str,
        top_k: int | None = None,
        filter_conditions: dict | None = None,
    ) -> list[dict]:
        """
        검색 후 중복 내용이 있는 문서를 제거하여 반환한다.
        오버랩 청킹으로 인해 유사한 내용의 청크가 중복 검색되는 경우를 처리한다.
        """
        # 중복 제거를 고려하여 요청 수보다 여유 있게 검색한다.
        k = top_k or self.top_k
        raw_results = await self.retrieve(
            query=query,
            top_k=k * 2,
            filter_conditions=filter_conditions,
        )

        # 텍스트 내용이 80% 이상 겹치는 결과를 중복으로 판단하여 제거한다.
        unique_results = []
        seen_texts = []

        for result in raw_results:
            text = result["text"]
            is_duplicate = False

            for seen in seen_texts:
                if self._similarity_ratio(text, seen) > 0.8:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_results.append(result)
                seen_texts.append(text)

            if len(unique_results) >= k:
                break

        return unique_results

    def _similarity_ratio(self, text1: str, text2: str) -> float:
        """
        두 텍스트의 단순 문자 겹침 비율을 계산한다.
        정확한 유사도 계산보다 빠른 처리가 목적이다.
        """
        if not text1 or not text2:
            return 0.0

        shorter = text1 if len(text1) <= len(text2) else text2
        longer = text2 if len(text1) <= len(text2) else text1

        if not longer:
            return 0.0

        matches = sum(1 for char in shorter if char in longer)
        return matches / len(longer)

    def format_context(self, results: list[dict]) -> str:
        """
        검색된 문서 목록을 LLM 프롬프트에 포함할 형식으로 변환한다.
        """
        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results):
            source = result.get("source", "알 수 없는 출처")
            page = result.get("page", "")
            text = result["text"]

            page_info = f" ({page}페이지)" if page else ""
            header = f"--- 참고 문서 {i + 1} | 출처: {source}{page_info} ---"
            context_parts.append(f"{header}\n{text}")

        return "\n\n".join(context_parts)


# 싱글톤 인스턴스
retriever = RetrieverService(top_k=5, score_threshold=0.5)
```

`score_threshold`는 RAG 시스템에서 자주 조정하게 되는 값이다. 너무 높게 설정하면 관련 문서가 있음에도 검색되지 않고, 너무 낮게 설정하면 관련 없는 문서가 포함되어 답변 품질이 저하된다. 내부 업무 문서의 특성과 실제 질문 패턴에 맞게 조정해야 한다.

---

## 9.3 RAG 프롬프트 구성

검색된 문서를 LLM에 전달하는 프롬프트를 구성한다. 여기서 핵심은 프론트엔드가 보낸 OpenAI 형식 메시지에 RAG 컨텍스트를 **투명하게 주입**하는 것이다. 프론트엔드는 표준 `messages` 배열을 전송하고, 백엔드가 이 배열을 가공하여 검색 결과를 삽입한 뒤 LLM에 전달한다.

```python
# services/rag_prompt.py


class RAGPromptBuilder:
    """
    RAG 시스템을 위한 프롬프트를 구성하는 클래스.

    프론트엔드가 보낸 OpenAI 호환 메시지 배열에 RAG 컨텍스트를 주입한다.
    프론트엔드 쪽에서는 RAG가 동작하는지 알 수 없다(투명 처리).
    """

    # RAG 모드에서 시스템 프롬프트 앞에 추가되는 지시문
    RAG_INSTRUCTION = (
        "당신은 조직의 내부 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.\n\n"
        "답변 시 다음 원칙을 반드시 준수하십시오.\n"
        "첫째, 아래 제공된 참고 문서의 내용을 우선적으로 활용하여 답변합니다.\n"
        "둘째, 참고 문서에 없는 내용은 '제공된 자료에서 해당 내용을 찾을 수 없습니다'라고 답변합니다.\n"
        "셋째, 답변 마지막에 참고한 문서의 출처를 표시합니다.\n"
        "넷째, 문서의 내용을 임의로 해석하거나 과장하지 않습니다."
    )

    def inject_rag_context(
        self,
        messages: list[dict],
        context: str,
    ) -> list[dict]:
        """
        프론트엔드가 보낸 OpenAI 형식 메시지 배열에 RAG 컨텍스트를 주입한다.

        전략:
        1. 기존 시스템 프롬프트가 있으면 RAG 지시문 + 컨텍스트를 앞에 추가한다.
        2. 시스템 프롬프트가 없으면 RAG 지시문 + 컨텍스트를 시스템 메시지로 삽입한다.
        3. 마지막 사용자 메시지는 그대로 유지한다(프론트엔드 UI에 표시되는 내용과 일치).

        이 방식은 프론트엔드의 대화 이력 구조를 훼손하지 않는다.
        """
        if not context:
            return messages

        # 메시지를 복사하여 원본을 변경하지 않는다.
        modified = [msg.copy() for msg in messages]

        context_block = (
            f"\n\n[참고 문서]\n{context}\n\n"
            "위 참고 문서를 바탕으로 사용자의 질문에 답변하세요."
        )

        # 시스템 메시지가 있는지 확인한다.
        system_idx = next(
            (i for i, m in enumerate(modified) if m["role"] == "system"),
            None
        )

        if system_idx is not None:
            # 기존 시스템 프롬프트에 RAG 지시문과 컨텍스트를 추가한다.
            original_system = modified[system_idx]["content"]
            modified[system_idx]["content"] = (
                f"{self.RAG_INSTRUCTION}\n\n"
                f"[기존 지시사항]\n{original_system}"
                f"{context_block}"
            )
        else:
            # 시스템 메시지가 없으면 RAG 시스템 메시지를 맨 앞에 삽입한다.
            modified.insert(0, {
                "role": "system",
                "content": f"{self.RAG_INSTRUCTION}{context_block}"
            })

        return modified

    def build_source_citation(self, results: list[dict]) -> str:
        """
        검색 결과의 출처 목록을 마크다운 형식으로 반환한다.
        스트리밍 응답 끝에 부록으로 추가할 수 있다.
        """
        if not results:
            return ""

        sources = []
        seen = set()
        for result in results:
            source = result.get("source", "")
            page = result.get("page", "")
            key = f"{source}_{page}"
            if source and key not in seen:
                seen.add(key)
                page_info = f" {page}p" if page else ""
                sources.append(f"📄 {source}{page_info}")

        return "\n".join(sources)


# 싱글톤 인스턴스
rag_prompt_builder = RAGPromptBuilder()
```

---

## 9.4 `/v1/chat/completions` 엔드포인트에 RAG 통합

기존 `/v1/chat/completions` 엔드포인트를 수정하여 RAG를 투명하게 적용한다. 프론트엔드는 기존과 동일한 OpenAI 형식 요청을 보내고, 백엔드가 내부적으로 RAG 검색→컨텍스트 주입→LLM 호출 과정을 수행한다.

### 설계 원칙

프론트엔드(예: NextChat)는 대화 이력(messages 배열)을 클라이언트에서 관리하여 매 요청마다 전체 이력을 전송한다. 백엔드는 **무상태(stateless)**이므로 `conversation_manager` 같은 서버 측 이력 관리가 필요 없다. 요청에 포함된 마지막 사용자 메시지를 추출하여 RAG 검색을 수행하고, 검색 결과를 메시지 배열에 주입한 뒤 LLM에 전달하면 된다.

```
프론트엔드 → POST /v1/chat/completions (표준 OpenAI 형식)
         ↓
백엔드: 마지막 user 메시지 추출
         ↓
백엔드: Qdrant 검색 → 관련 문서 획득
         ↓
백엔드: messages에 RAG 컨텍스트 주입
         ↓
백엔드: HyperCLOVA X에 전달 → 응답 스트리밍
         ↓
프론트엔드 ← SSE 스트리밍 응답 (표준 OpenAI 형식)
```

### 채팅 라우터 수정

```python
# routers/chat.py
import json
import time
import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse, JSONResponse

from models.chat import ChatCompletionRequest
from services.llm import llm_service
from services.retriever import retriever
from services.rag_prompt import rag_prompt_builder

router = APIRouter(tags=["chat"])


@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI 호환 Chat Completions 엔드포인트.
    프론트엔드가 보내는 표준 요청을 받아 RAG 검색 후 응답한다.

    RAG는 항상 수행된다. 검색 결과가 없으면 RAG 컨텍스트 없이
    원본 메시지를 그대로 LLM에 전달한다.
    """
    messages = [msg.model_dump() for msg in request.messages]

    # ── 1. 마지막 사용자 메시지 추출 ──
    last_user_msg = None
    for msg in reversed(messages):
        if msg["role"] == "user":
            last_user_msg = msg["content"]
            break

    # ── 2. RAG 검색 ──
    rag_context = ""
    if last_user_msg:
        search_results = await retriever.retrieve_with_dedup(
            query=last_user_msg,
            top_k=5,
        )
        if search_results:
            rag_context = retriever.format_context(search_results)

    # ── 3. RAG 컨텍스트 주입 ──
    if rag_context:
        messages = rag_prompt_builder.inject_rag_context(
            messages=messages,
            context=rag_context,
        )

    # ── 4. LLM 호출 ──
    if request.stream:
        return _stream_response(messages, request.model)
    else:
        return await _normal_response(messages, request.model)


async def _normal_response(
    messages: list[dict],
    model: str,
) -> JSONResponse:
    """비스트리밍 방식으로 OpenAI 호환 응답을 반환한다."""
    answer = await llm_service.generate(messages)

    response_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    return JSONResponse(content={
        "id": response_id,
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": answer},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    })


def _stream_response(
    messages: list[dict],
    model: str,
) -> StreamingResponse:
    """SSE 스트리밍 방식으로 OpenAI 호환 응답을 반환한다."""
    response_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

    async def generate():
        async for chunk_text in llm_service.generate_stream(messages):
            chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": chunk_text},
                    "finish_reason": None,
                }],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

        # 종료 청크
        done_chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop",
            }],
        }
        yield f"data: {json.dumps(done_chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

### 프론트엔드와의 통합 포인트

위 코드에서 주목할 점이 있다.

**프론트엔드는 아무것도 모른다.** 프론트엔드는 평소처럼 사용자 메시지를 포함한 `messages` 배열을 `/v1/chat/completions`에 POST한다. 백엔드는 마지막 사용자 메시지로 Qdrant를 검색하고, 결과가 있으면 시스템 프롬프트에 컨텍스트를 주입한 뒤 LLM에 전달한다. 응답은 표준 OpenAI SSE 스트리밍이므로 프론트엔드가 그대로 렌더링한다.

**RAG는 항상 시도된다.** 별도의 `use_rag` 플래그 없이, 매 요청마다 검색을 수행한다. 관련 문서가 없으면(`score_threshold` 미만) 컨텍스트 없이 원본 메시지를 LLM에 전달하므로, 일반 대화와 문서 기반 대화가 자연스럽게 전환된다.

**대화 이력은 프론트엔드가 관리한다.** 서버는 무상태이다. 프론트엔드(예: NextChat)가 매 요청에 전체 대화 이력을 포함하므로, 서버 측에서 `conversation_manager`나 세션 관리가 필요 없다.

---

## 9.5 프론트엔드 설정 — RAG 동작에 필요한 설정

프론트엔드 코드를 수정할 필요는 없지만, 시스템 프롬프트 설정이 RAG 품질에 영향을 준다. 프론트엔드 설정에서 시스템 프롬프트를 지정하면, 백엔드의 `inject_rag_context`가 해당 프롬프트를 보존하면서 RAG 지시문을 앞에 추가한다.

### 권장 시스템 프롬프트

프론트엔드 설정에서 다음과 같은 시스템 프롬프트를 지정한다.

```
당신은 조직의 내부 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.
정확하고 이해하기 쉬운 언어로 답변합니다.
확인되지 않은 내용은 모른다고 솔직하게 명시합니다.
```

이 프롬프트는 프론트엔드(예: NextChat)가 매 요청의 `messages[0]`에 `system` 역할로 포함하여 전송한다. 백엔드의 `inject_rag_context`는 이 내용을 `[기존 지시사항]`으로 보존하고, RAG 지시문과 검색된 문서를 추가한다.

### 환경 변수 확인

제5장에서 설정한 프론트엔드 환경 변수가 그대로 적용된다. 추가 설정은 필요 없다.

**Streamlit** (`frontend/.env`):
```bash
BACKEND_URL=http://localhost:8000
```

**NextChat** (`frontend/.env.local`):
```bash
BASE_URL=http://localhost:8000
CUSTOM_MODELS=-all,+HyperCLOVA-X
DEFAULT_MODEL=HyperCLOVA-X
NEXT_PUBLIC_SITE_TITLE=내부 문서 AI 챗봇
HIDE_USER_API_KEY=1
HIDE_BALANCE_QUERY=1
```

### 프론트엔드별 차이

RAG 관련 기능은 프론트엔드에 따라 처리 방식이 다르다.

| 기능 | Streamlit (학습용) | NextChat (프로덕션 대안) |
|------|-----------|----------|
| 문서 업로드 | 사이드바 파일 업로더 | Swagger UI 또는 curl (관리자 전용) |
| RAG 토글 | UI 토글 스위치 | 항상 활성 (백엔드 자동 처리) |
| 출처 표시 | 접을 수 있는 섹션 | LLM 응답 본문에 포함 (프롬프트 지시) |
| 대화 이력 | 서버 세션 관리 | 클라이언트 관리 |

출처 표시는 RAG 프롬프트의 "답변 마지막에 참고한 문서의 출처를 표시합니다" 지시에 의해 LLM이 응답 본문에 직접 포함한다. 별도의 UI 컴포넌트가 필요 없다.

---

## 9.6 RAG 동작 확인

모든 서비스를 실행하고 RAG가 실제로 동작하는지 확인한다.

### 서비스 전체 실행

```bash
# 
docker compose up -d --build
```

세 서비스가 모두 정상 실행되는지 확인한다.

```bash
docker compose ps
# NAME                 STATUS
# chatbot-frontend        Up (healthy)
# chatbot-backend         Up (healthy)
# chatbot-qdrant          Up (healthy)
```

### 문서 업로드

Swagger UI(`http://localhost:8000/docs`)에서 테스트 문서를 업로드한다.

```bash
# 또는 curl로 업로드
curl -X POST "http://localhost:8000/documents/upload" \
  -F "file=@test_document.txt"
```

`/documents/info`를 호출하여 인덱싱된 벡터 수가 증가했는지 확인한다.

### 프론트엔드에서 RAG 확인

브라우저에서 Streamlit(`http://localhost:8501`) 또는 NextChat(`http://localhost:3000`)에 접속한다. 채팅창에 업로드한 문서와 관련된 질문을 입력한다.

```
연차 휴가 신청 절차가 어떻게 되나요?
```

응답에 업로드한 문서의 내용(뉴턴의 제3법칙, 추진제 연소 등)이 반영되고, 답변 끝에 출처가 표시된다면 RAG가 정상 동작하는 것이다.

문서에 없는 내용을 질문하면 "제공된 자료에서 해당 내용을 찾을 수 없습니다"라는 응답이 나타나야 한다.

### 단계별 확인 방법

문제가 발생했을 때 어느 단계에서 오류가 발생했는지 확인하려면 다음 순서로 점검한다.

먼저 Qdrant 대시보드(`http://localhost:6333/dashboard`)에서 `documents` 컬렉션의 포인트 수가 0보다 큰지 확인한다. 포인트가 있다면 인덱싱은 정상이다.

다음으로 검색이 잘 되는지 백엔드 API를 직접 호출한다. `http://localhost:8000/docs`에서 `POST /v1/chat/completions`를 `stream: false`로 호출하면 스트리밍 없이 응답을 확인할 수 있다.

```json
{
  "model": "HyperCLOVA-X",
  "messages": [
    {"role": "user", "content": "출장비 정산 방법을 알려주세요."}
  ],
  "stream": false
}
```

백엔드 로그를 확인하여 RAG 검색 결과를 살펴본다.

```bash
docker compose logs -f backend
```

---

## 9.7 RAG 품질 튜닝

RAG 시스템을 실제 내부 업무 문서와 질문 패턴으로 테스트하다 보면 품질을 개선해야 할 상황이 생긴다. 주요 튜닝 포인트를 정리한다.

### 검색 결과가 너무 적거나 없는 경우

`score_threshold` 값을 낮춘다. `services/retriever.py`에서 `RetrieverService` 인스턴스 생성 시 값을 조정한다.

```python
# 기본값 0.5에서 낮춤
retriever = RetrieverService(top_k=5, score_threshold=0.4)
```

또는 `top_k` 값을 늘려 더 많은 후보를 가져온다.

### 관련 없는 문서가 검색되는 경우

`score_threshold` 값을 높인다. 혹은 청크 크기를 줄여 각 청크가 더 집중된 내용을 담도록 한다.

```python
# chunker.py의 기본 청커 재설정
default_chunker = RecursiveTextChunker(
    chunk_size=300,   # 500에서 줄임
    chunk_overlap=30
)
```

### 답변이 문서 내용과 맞지 않는 경우

RAG 시스템 프롬프트를 강화한다. `rag_prompt.py`의 `RAG_INSTRUCTION`에 더 강한 제약 조건을 추가한다.

### 짧은 질문에서 검색 성능이 낮은 경우

"그거 어떻게 돼요?" 같은 짧은 질문은 검색 성능이 낮다. 프론트엔드가 보내는 대화 이력을 활용하여 질문을 재작성한 뒤 검색하는 기법을 적용할 수 있다.

```python
# 질문 재작성 예시 (services/retriever.py에 추가)
async def rewrite_query(
    self,
    query: str,
    messages: list[dict]
) -> str:
    """
    대화 이력을 참조하여 검색에 최적화된 형태로 질문을 재작성한다.

    프론트엔드(예: NextChat)는 매 요청에 전체 대화 이력을 포함하므로,
    이전 대화 맥락을 참조할 수 있다.
    """
    if len(query) > 20 or len(messages) < 3:
        return query

    # 최근 대화만 참조한다.
    recent = [m for m in messages[-4:] if m["role"] != "system"]
    context_text = "\n".join(
        f"{m['role']}: {m['content']}" for m in recent
    )

    rewrite_messages = [
        {
            "role": "system",
            "content": (
                "주어진 대화 맥락을 참고하여 마지막 질문을 "
                "검색에 적합한 완전한 문장으로 재작성하세요. "
                "재작성된 질문만 출력하고 다른 내용은 포함하지 마세요."
            )
        },
        {
            "role": "user",
            "content": f"대화 맥락:\n{context_text}\n\n마지막 질문: {query}"
        }
    ]

    from services.llm import llm_service
    rewritten = await llm_service.generate(
        rewrite_messages, temperature=0.1, max_tokens=100
    )
    return rewritten.strip()
```

이 기법을 적용하려면 `chat_completions` 핸들러에서 `retrieve_with_dedup` 호출 전에 `rewrite_query`를 실행하면 된다. 다만 LLM을 한 번 더 호출하므로 지연 시간이 늘어나는 점을 고려해야 한다.

---

## 9.8 현재까지의 파일 구조

```
backend/
├── .dockerignore
├── Dockerfile
├── requirements.txt
├── main.py
├── config.py
├── test_vector_store.py
├── test_indexing.py
├── test_document.txt
├── routers/
│   ├── __init__.py
│   ├── chat.py                 # RAG 통합된 /v1/chat/completions
│   └── documents.py
├── services/
│   ├── __init__.py
│   ├── llm.py
│   ├── embeddings.py
│   ├── conversation.py         # 메시지 전처리 유틸리티 (4장에서 작성)
│   ├── vector_store.py
│   ├── document_loader.py
│   ├── chunker.py
│   ├── indexer.py
│   ├── retriever.py            # 검색 서비스 (신규)
│   └── rag_prompt.py           # RAG 프롬프트 구성 (신규)
└── models/
    ├── __init__.py
    ├── chat.py
    └── document.py
```

전체 서비스 구성(프론트엔드, 백엔드, Qdrant)은 `docker-compose.yml`에서 관리한다. 프론트엔드(`frontend`)는 이 장에서 코드 변경 없이 기존 설정 그대로 동작한다.

변경 사항을 커밋한다.

```bash
git add .
git commit -m "feat: RAG 검색/생성 파이프라인을 /v1/chat/completions에 통합

- 검색 서비스: Qdrant 유사도 검색 + 중복 제거
- RAG 프롬프트: OpenAI 메시지 배열에 투명 컨텍스트 주입
- /v1/chat/completions: 매 요청마다 자동 RAG 수행
- 프론트엔드 코드 변경 없음 (투명 통합)"
```

---

## 9.9 2단계 완성 및 3단계 안내

이 장까지의 작업으로 외부 API 기반 RAG 챗봇이 완성되었다. 지금까지 구축한 시스템을 정리하면 다음과 같다.

관리자가 Swagger UI를 통해 내부 업무 문서를 업로드하면, 텍스트가 추출되고 청킹과 임베딩을 거쳐 Qdrant의 `documents` 컬렉션에 저장된다. 사용자가 프론트엔드에서 질문을 입력하면, 프론트엔드는 `/v1/chat/completions`에 표준 OpenAI 형식으로 요청을 보낸다. 백엔드는 마지막 사용자 메시지로 Qdrant를 검색하고, 관련 문서를 찾으면 시스템 프롬프트에 컨텍스트를 주입한 뒤 HyperCLOVA X에 전달한다. 문서를 근거로 한 답변이 SSE 스트리밍으로 프론트엔드에 반환된다.

이 시스템은 외부 네트워크를 통해 HyperCLOVA X API와 임베딩 API를 호출한다. 다음 단계에서는 이 두 가지 외부 API 호출을 로컬에서 실행되는 LLM과 임베딩 모델로 교체하여 완전한 폐쇄형 시스템을 완성한다.

교체해야 할 파일은 단 두 개다. `services/llm.py`의 `llm_service`와 `services/embeddings.py`의 `embedding_service`를 처음부터 이 점을 염두에 두고 설계했기 때문이다. `/v1/chat/completions` 핸들러, RAG 파이프라인, 프론트엔드는 전혀 수정하지 않아도 된다.

3단계에서는 GPU 서버를 준비하고, 오픈소스 LLM과 임베딩 모델을 내려받고, 로컬 서버를 구동하여 API를 교체하는 과정을 진행한다.

---

이것으로 제9장의 내용을 마친다. 다음 장부터는 3단계로 넘어가 로컬 LLM 환경을 준비하고 서비스를 구동하는 방법을 다룬다.
