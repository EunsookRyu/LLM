# 제4장. HyperCLOVA X API로 챗봇 백엔드 구축하기

## 4.1 HyperCLOVA X와 CLOVA Studio

HyperCLOVA X는 네이버가 개발한 대규모 언어 모델이다. 한국어 데이터를 대량으로 학습하였기 때문에 한국어 이해와 생성 능력이 뛰어나며, 한국 문화와 맥락에 대한 이해도가 높다. 외부 API 기반으로 챗봇을 구축하는 이 가이드의 1단계에서 HyperCLOVA X를 사용하는 이유는 이 때문이다.

CLOVA Studio는 HyperCLOVA X를 비롯한 네이버의 AI 모델을 API 형태로 제공하는 플랫폼이다. 회원가입 후 API 키를 발급받으면 HTTP 요청으로 LLM을 호출할 수 있다. 3단계에서 로컬 LLM으로 교체할 때, 이 HTTP 요청 방식을 그대로 유지하되 엔드포인트 주소만 바꾸는 방식으로 전환이 이루어진다. 처음부터 이를 염두에 두고 코드를 작성하는 것이 중요하다.

---

## 4.2 CLOVA Studio 가입 및 API 키 발급

### 가입 절차

브라우저에서 `https://clova.ai/studio`에 접속한다. 네이버 계정으로 로그인하거나 새 계정을 생성한다. 최초 접속 시 서비스 이용 약관 동의 화면이 나타난다. 내용을 확인하고 동의한다.

로그인 후 대시보드 화면이 나타난다. 상단 메뉴에서 "API 키 관리" 또는 "테스트 앱" 항목을 찾는다. CLOVA Studio의 UI는 업데이트에 따라 변경될 수 있으므로, 정확한 메뉴 위치는 공식 문서를 함께 참조한다.

### API 키 발급

CLOVA Studio에서 사용하는 인증 방식은 두 가지 키의 조합이다.

**API 키**는 사용자 또는 앱을 식별하는 키다. 요청 헤더의 `X-NCP-CLOVASTUDIO-API-KEY` 항목에 입력한다.

**API Gateway 키**는 네이버 클라우드 플랫폼의 API Gateway를 통해 요청을 인증하는 키다. 요청 헤더의 `X-NCP-APIGW-API-KEY` 항목에 입력한다.

테스트 앱을 생성하면 두 키가 함께 발급된다. 발급된 키는 화면을 닫으면 다시 확인하기 어려운 경우가 있으므로, 즉시 `.env` 파일에 저장한다.

```
CLOVA_API_KEY=발급받은_API_키
CLOVA_API_GATEWAY_KEY=발급받은_API_Gateway_키
```

### 요금 및 사용량 확인

CLOVA Studio는 일정 수준의 무료 크레딧을 제공한다. 크레딧 사용량은 대시보드에서 확인할 수 있다. 이 가이드를 따라 개발하는 과정에서의 사용량은 무료 범위 내에 해당하는 경우가 많지만, 운영 환경에서 사용량이 늘어날 경우 요금이 발생할 수 있으므로 주기적으로 확인하는 것이 좋다.

---

## 4.3 API 구조 이해

실제 코드를 작성하기 전에 HyperCLOVA X의 API 요청과 응답 구조를 먼저 이해한다.

### 엔드포인트

HyperCLOVA X 채팅 완성 API의 기본 엔드포인트는 다음과 같다.

```
POST https://clovastudio.stream.ntruss.com/testapp/v1/chat-completions/HCX-003
```

`HCX-003`은 모델 버전이다. CLOVA Studio에서 제공하는 모델 버전은 업데이트에 따라 변경될 수 있다. 현재 사용 가능한 모델 목록은 CLOVA Studio 공식 문서에서 확인한다.

### 요청 형식

요청 본문은 JSON 형식이다.

```json
{
  "messages": [
    {
      "role": "system",
      "content": "당신은 조직의 내부 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다."
    },
    {
      "role": "user",
      "content": "안녕하세요, 내부 업무 프로그램이 궁금합니다."
    }
  ],
  "topP": 0.8,
  "topK": 0,
  "maxTokens": 512,
  "temperature": 0.5,
  "repeatPenalty": 5.0,
  "stopBefore": [],
  "includeAiFilters": true
}
```

각 파라미터의 역할을 이해하는 것이 중요하다.

**messages**는 대화 이력 배열이다. 각 메시지는 `role`과 `content`를 가진다. `role`은 세 가지 값 중 하나를 가진다. `system`은 모델의 역할과 행동 방식을 정의하는 시스템 프롬프트다. `user`는 사용자의 입력이다. `assistant`는 모델의 이전 응답이다. 멀티턴 대화를 구현하려면 이전 대화 이력을 `messages` 배열에 순서대로 포함시켜야 한다.

**temperature**는 응답의 무작위성을 조절하는 값으로, 0에서 1 사이의 실수다. 값이 낮을수록 일관성 있고 예측 가능한 응답을 생성하고, 높을수록 다양하고 창의적인 응답을 생성한다. 사실 기반의 답변이 중요한 챗봇에는 낮은 값을, 창작 도구에는 높은 값을 사용한다.

**maxTokens**는 응답에서 생성할 최대 토큰 수다. 토큰은 대략 한 단어 또는 한 음절에 해당하는 텍스트 단위다. 값이 너무 작으면 응답이 중간에 잘릴 수 있고, 너무 크면 불필요하게 긴 응답이 생성될 수 있다.

**topP**와 **topK**는 생성할 다음 토큰의 후보군을 제한하는 파라미터다. 일반적으로는 기본값을 사용한다.

**repeatPenalty**는 같은 내용을 반복하는 것에 대한 패널티다. 값이 높을수록 반복을 억제한다.

### 응답 형식

스트리밍을 사용하지 않는 경우의 응답은 다음과 같다.

```json
{
  "status": {
    "code": "20000",
    "message": "OK"
  },
  "result": {
    "message": {
      "role": "assistant",
      "content": "안녕하세요! 우리 조직의 교육 프로그램에 대해 안내해 드리겠습니다..."
    },
    "stopReason": "length",
    "inputLength": 42,
    "outputLength": 128
  }
}
```

응답 텍스트는 `result.message.content`에서 추출한다.

### 스트리밍 응답

LLM은 응답 전체를 한 번에 생성하지 않고 토큰을 하나씩 순차적으로 생성한다. 스트리밍을 사용하면 생성된 토큰을 즉시 클라이언트에 전송할 수 있어, 사용자가 응답이 완성될 때까지 기다리지 않고 글자가 타이핑되는 것처럼 실시간으로 확인할 수 있다. 챗봇 UX에서 스트리밍은 사실상 필수 기능이다.

스트리밍 엔드포인트는 기본 엔드포인트와 동일하지만, 응답 형식이 Server-Sent Events 방식으로 반환된다. 각 이벤트는 다음과 같은 형식이다.

```
data: {"message":{"role":"assistant","content":"안"},"stopReason":null,"inputLength":42,"outputLength":1}

data: {"message":{"role":"assistant","content":"녕"},"stopReason":null,"inputLength":42,"outputLength":2}

data: [DONE]
```

---

## 4.4 LLM 서비스 모듈 작성

이제 실제 코드를 작성한다. 앞서 설계한 구조에 따라 `services/llm.py`에 HyperCLOVA X API를 호출하는 로직을 작성한다. 이 모듈이 나중에 교체할 대상이므로, 인터페이스를 명확하게 정의하는 것이 핵심이다.

이 프로젝트의 백엔드는 **OpenAI API 호환 형식**으로 프론트엔드와 통신한다. 이렇게 설계하면 Streamlit, NextChat 등 어떤 OpenAI 호환 프론트엔드든 연결할 수 있다. LLM 서비스 모듈은 내부적으로 HyperCLOVA X API를 호출하되, 외부(라우터)에는 OpenAI 호환 인터페이스를 노출한다. 이 구조 덕분에 나중에 로컬 LLM(Ollama, vLLM 등)으로 교체할 때에도 라우터 코드를 전혀 수정하지 않아도 된다.

### 비동기 HTTP 클라이언트 설치

Python에서 비동기 HTTP 요청을 처리하는 데 가장 널리 사용되는 라이브러리는 `httpx`다. `requests` 라이브러리와 사용법이 유사하지만 비동기를 지원한다.

```bash
pip install httpx
```

### LLM 서비스 모듈

```python
# services/llm.py
import httpx
import json
from typing import AsyncGenerator
from config import config


class HyperClovaXService:
    """
    HyperCLOVA X API를 호출하는 서비스 클래스.

    나중에 로컬 LLM으로 교체할 때 이 클래스를 대체한다.
    외부에서는 generate()와 generate_stream() 메서드만 사용하므로,
    교체 시 동일한 인터페이스를 유지하면 된다.
    """

    BASE_URL = "https://clovastudio.stream.ntruss.com/testapp/v1"
    MODEL = "HCX-003"

    def __init__(self):
        self.headers = {
            "X-NCP-CLOVASTUDIO-API-KEY": config.CLOVA_API_KEY,
            "X-NCP-APIGW-API-KEY": config.CLOVA_API_GATEWAY_KEY,
            "Content-Type": "application/json",
        }

    def _build_request_body(
        self,
        messages: list[dict],
        temperature: float = 0.5,
        max_tokens: int = 512,
    ) -> dict:
        """
        OpenAI 형식의 messages를 HyperCLOVA X 요청 본문으로 변환한다.
        외부에서 전달받는 messages는 OpenAI 형식
        (role: system/user/assistant, content: str)이므로
        HyperCLOVA X에서도 그대로 사용할 수 있다.
        """
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
        """
        단일 응답을 생성하여 완성된 텍스트를 반환한다.
        스트리밍이 필요 없는 경우에 사용한다.
        """
        url = f"{self.BASE_URL}/chat-completions/{self.MODEL}"
        body = self._build_request_body(messages, temperature, max_tokens)

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
        """
        스트리밍 방식으로 응답을 생성한다.
        토큰이 생성될 때마다 yield로 반환한다.
        """
        url = f"{self.BASE_URL}/chat-completions/{self.MODEL}"
        body = self._build_request_body(messages, temperature, max_tokens)

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


# 모듈 수준에서 인스턴스를 생성하여 싱글톤으로 사용한다.
# 교체 시 이 한 줄만 변경하면 된다.
llm_service = HyperClovaXService()
```

이 모듈에서 특히 주목해야 할 부분은 마지막 줄의 `llm_service = HyperClovaXService()`이다. 라우터를 비롯한 다른 모듈에서는 `HyperClovaXService` 클래스를 직접 참조하지 않고 `llm_service` 객체를 임포트하여 사용한다. 나중에 로컬 LLM 서비스 클래스로 교체할 때 이 한 줄만 바꾸면 다른 파일은 전혀 수정하지 않아도 된다.

---

## 4.5 메시지 전처리 유틸리티

멀티턴 대화를 구현하려면 이전 대화 내용을 기억하고 다음 요청에 포함시켜야 한다. HyperCLOVA X는 상태를 직접 관리하지 않으므로, 매 요청 시 전체 대화 이력을 전송해야 한다.

### 프론트엔드에서의 대화 이력 관리

NextChat과 같은 OpenAI 호환 프론트엔드는 **클라이언트 측에서 대화 이력을 관리**한다. 사용자가 메시지를 보낼 때마다 프론트엔드는 이전 대화 이력 전체를 `messages` 배열에 포함하여 백엔드에 전송한다. 따라서 백엔드는 **상태 비저장(stateless)** 방식으로 동작할 수 있다. 매 요청마다 전달받은 `messages`를 그대로 LLM에 전달하고 응답을 반환하면 된다.

이 방식의 장점은 다음과 같다.

- 백엔드 서버가 재시작되어도 대화가 끊기지 않는다.
- 수평 확장(서버 여러 대 운영)이 용이하다. 어느 서버로 요청이 가더라도 동일한 결과를 얻는다.
- 서버 메모리를 대화 이력 저장에 사용하지 않아도 된다.

다만 서버 측에서 대화 이력을 관리할 필요가 있는 경우도 있다. 대표적인 예가 RAG(Retrieval-Augmented Generation)다. 사용자가 보낸 메시지를 기반으로 관련 문서를 검색하고, 검색 결과를 시스템 프롬프트에 주입해야 하기 때문이다. 이 경우에도 기본적인 대화 턴 관리는 프론트엔드가 담당하고, 백엔드는 전달받은 `messages`를 **가공**(문서 검색 결과 삽입 등)하는 역할만 수행한다.

### 서버 측 메시지 전처리 유틸리티

백엔드는 대화 이력을 직접 저장하지 않지만, 프론트엔드에서 전달받은 `messages` 배열을 LLM에 넘기기 전에 전처리하는 역할은 담당한다. 시스템 프롬프트가 빠진 요청에 기본값을 채워 넣고, 이력이 지나치게 길어졌을 때 오래된 메시지를 정리하는 두 가지 유틸리티를 작성한다.

> **9장에서의 확장**: 이 유틸리티는 9장에서 RAG를 통합할 때 `services/rag_prompt.py`와 함께 사용된다. `rag_prompt.py`가 시스템 프롬프트에 검색 결과를 주입하는 역할을 추가로 담당하며, `conversation.py`의 두 함수는 그 전처리 단계로 동작한다.

```python
# services/conversation.py
from typing import Optional


# 기본 시스템 프롬프트
DEFAULT_SYSTEM_PROMPT = (
    "당신은 조직의 내부 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다. "
    "내부 업무과 관련된 질문에 정확하고 도움이 되는 답변을 제공합니다. "
    "모르는 내용에 대해서는 솔직하게 모른다고 답합니다."
)


def ensure_system_prompt(
    messages: list[dict],
    system_prompt: Optional[str] = None,
) -> list[dict]:
    """
    messages 배열에 시스템 프롬프트가 없으면 추가한다.
    프론트엔드(예: NextChat)가 시스템 프롬프트를 포함하지 않는 경우에 대비한다.
    """
    prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    if not messages or messages[0].get("role") != "system":
        return [{"role": "system", "content": prompt}] + messages

    return messages


def trim_messages(
    messages: list[dict],
    max_messages: int = 20,
) -> list[dict]:
    """
    대화 이력이 너무 길어지면 오래된 메시지를 제거한다.
    시스템 프롬프트는 항상 유지하고,
    그 이후 메시지 중 가장 최근 max_messages개만 유지한다.

    프론트엔드(예: NextChat)도 자체적으로 이력을 제한하지만,
    서버 측에서도 방어적으로 제한하여 LLM API 비용을 절감한다.
    """
    if len(messages) <= max_messages + 1:  # +1은 시스템 프롬프트
        return messages

    system_message = messages[0] if messages[0].get("role") == "system" else None
    recent_messages = messages[-(max_messages):]

    if system_message and recent_messages[0].get("role") != "system":
        return [system_message] + recent_messages
    return recent_messages
```

원본 가이드에서는 대화 ID 기반의 `ConversationManager` 클래스를 사용하여 서버 메모리에 대화 이력을 저장했다. OpenAI 호환 프론트엔드 아키텍처에서는 클라이언트가 이력을 관리하므로 이 방식이 필요 없다. 대신 요청마다 전달받은 `messages`를 가공하는 전처리 유틸리티 함수들로 대체한다.

---

## 4.6 데이터 모델 정의 — OpenAI 호환 형식

프론트엔드는 OpenAI API 규격으로 백엔드와 통신한다. 따라서 요청과 응답의 데이터 구조를 OpenAI 호환 형식에 맞춰 Pydantic 모델로 정의한다. 이 형식을 따르면 NextChat, Streamlit 등 어떤 OpenAI 호환 프론트엔드든 연결할 수 있다.

```python
# models/chat.py
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import uuid


class Message(BaseModel):
    """개별 메시지"""
    role: str = Field(..., description="system, user, 또는 assistant")
    content: str = Field(..., description="메시지 내용")


class ChatCompletionRequest(BaseModel):
    """OpenAI 호환 채팅 완성 요청"""
    model: str = Field(default="HyperCLOVA-X", description="모델 이름")
    messages: List[Message] = Field(..., description="대화 이력")
    temperature: Optional[float] = Field(default=0.5, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=512, ge=1)
    stream: Optional[bool] = Field(default=False, description="스트리밍 여부")

    class Config:
        json_schema_extra = {
            "example": {
                "model": "HyperCLOVA-X",
                "messages": [
                    {"role": "system", "content": "당신은 친절한 AI입니다."},
                    {"role": "user", "content": "안녕하세요!"}
                ],
                "temperature": 0.5,
                "max_tokens": 512,
                "stream": False
            }
        }


class Choice(BaseModel):
    """응답 선택지"""
    index: int = 0
    message: Message
    finish_reason: str = "stop"


class Usage(BaseModel):
    """토큰 사용량"""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI 호환 채팅 완성 응답 (비스트리밍)"""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "HyperCLOVA-X"
    choices: List[Choice]
    usage: Optional[Usage] = None


# 스트리밍 응답용 모델
class DeltaMessage(BaseModel):
    """스트리밍 응답의 부분 메시지"""
    role: Optional[str] = None
    content: Optional[str] = None


class StreamChoice(BaseModel):
    """스트리밍 응답 선택지"""
    index: int = 0
    delta: DeltaMessage
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """OpenAI 호환 스트리밍 청크"""
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: str = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "HyperCLOVA-X"
    choices: List[StreamChoice]
```

OpenAI API 형식을 따르는 이유를 다시 강조하면 다음과 같다.

- **프론트엔드 호환**: OpenAI API 형식을 따르면 NextChat, Streamlit 등 어떤 OpenAI 호환 프론트엔드든 연결할 수 있다. 예를 들어 NextChat은 `BASE_URL`을 설정하면 `{BASE_URL}/v1/chat/completions`로 요청을 보낸다.
- **교체 용이성**: 나중에 vLLM이나 Ollama 같은 로컬 LLM 서빙 도구로 교체할 때, 이들 역시 OpenAI 호환 API를 제공하므로 전환이 매끄럽다.
- **생태계 호환**: LangChain, LlamaIndex 등 주요 프레임워크가 OpenAI API 형식을 표준으로 사용한다.

---

## 4.7 채팅 라우터 작성

라우터에서는 요청을 받아 서비스 모듈을 호출하고 응답을 반환하는 역할을 담당한다. 비즈니스 로직은 서비스 모듈에 위임한다.

프론트엔드(예: NextChat)는 스트리밍 모드에서 **OpenAI SSE 형식**의 응답을 기대하므로, 스트리밍 라우터도 해당 형식에 맞춰 구현해야 한다.

```python
# routers/chat.py
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import uuid
import time

from models.chat import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChunk,
    Choice,
    StreamChoice,
    Message,
    DeltaMessage,
    Usage,
)
from services.llm import llm_service
from services.conversation import ensure_system_prompt, trim_messages

router = APIRouter(tags=["chat"])


@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    OpenAI 호환 채팅 완성 엔드포인트.
    프론트엔드에서 보내는 요청을 처리한다.
    stream=True이면 스트리밍 방식으로, False이면 일반 방식으로 응답한다.
    """
    # messages를 dict 리스트로 변환
    messages = [m.model_dump() for m in request.messages]

    # 시스템 프롬프트가 없으면 기본값을 삽입한다.
    messages = ensure_system_prompt(messages)

    # 이력이 너무 길어지지 않도록 정리한다.
    messages = trim_messages(messages)

    if request.stream:
        return await _stream_response(messages, request)
    else:
        return await _normal_response(messages, request)


async def _normal_response(
    messages: list[dict],
    request: ChatCompletionRequest,
) -> ChatCompletionResponse:
    """비스트리밍 방식으로 응답을 반환한다."""
    try:
        answer = await llm_service.generate(
            messages,
            temperature=request.temperature or 0.5,
            max_tokens=request.max_tokens or 512,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM 서비스 오류: {str(e)}")

    return ChatCompletionResponse(
        model=request.model,
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content=answer),
                finish_reason="stop",
            )
        ],
        usage=Usage(),
    )


async def _stream_response(
    messages: list[dict],
    request: ChatCompletionRequest,
) -> StreamingResponse:
    """
    OpenAI SSE 형식으로 스트리밍 응답을 반환한다.
    프론트엔드는 이 형식으로 실시간 토큰을 화면에 표시한다.
    """
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    async def generate():
        try:
            # 첫 번째 청크: role을 전송한다.
            first_chunk = ChatCompletionChunk(
                id=completion_id,
                created=created,
                model=request.model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta=DeltaMessage(role="assistant"),
                    )
                ],
            )
            yield f"data: {first_chunk.model_dump_json()}\n\n"

            # 콘텐츠 청크를 순차적으로 전송한다.
            async for chunk in llm_service.generate_stream(
                messages,
                temperature=request.temperature or 0.5,
                max_tokens=request.max_tokens or 512,
            ):
                content_chunk = ChatCompletionChunk(
                    id=completion_id,
                    created=created,
                    model=request.model,
                    choices=[
                        StreamChoice(
                            index=0,
                            delta=DeltaMessage(content=chunk),
                        )
                    ],
                )
                yield f"data: {content_chunk.model_dump_json()}\n\n"

            # 마지막 청크: finish_reason을 전송한다.
            final_chunk = ChatCompletionChunk(
                id=completion_id,
                created=created,
                model=request.model,
                choices=[
                    StreamChoice(
                        index=0,
                        delta=DeltaMessage(),
                        finish_reason="stop",
                    )
                ],
            )
            yield f"data: {final_chunk.model_dump_json()}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as e:
            error_data = json.dumps(
                {"error": {"message": f"LLM 서비스 오류: {str(e)}"}},
                ensure_ascii=False,
            )
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
```

원본 가이드에서는 자체 정의한 SSE 형식(`{"chunk": "..."}`)을 사용했지만, 이 수정본에서는 OpenAI 표준 SSE 형식(`{"choices":[{"delta":{"content":"..."}}]}`)을 따른다. 이렇게 해야 NextChat, Streamlit 등 OpenAI 호환 프론트엔드가 스트리밍 응답을 올바르게 파싱하여 화면에 실시간으로 표시할 수 있다.

---

## 4.8 FastAPI 앱 진입점 작성

모든 라우터를 통합하고 앱의 전체 설정을 담당하는 `main.py`를 작성한다.

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat

app = FastAPI(
    title="내부 문서 AI 챗봇 API",
    description="HyperCLOVA X 기반 챗봇 API. 이후 로컬 LLM으로 교체 가능.",
    version="1.0.0",
)

# CORS 설정
# 프론트엔드(Streamlit, NextChat 등)에서의 API 요청을 허용한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",    # Streamlit 개발 서버
        "http://localhost:3000",    # NextChat 개발 서버
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(chat.router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "내부 문서 AI 챗봇 API가 실행 중입니다."}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

### CORS에 대하여

CORS는 Cross-Origin Resource Sharing의 약자다. 브라우저는 보안 정책상 다른 출처의 리소스에 대한 요청을 기본적으로 차단한다. 프론트엔드는 `http://localhost:8501`(Streamlit) 또는 `http://localhost:3000`(NextChat)에서, 백엔드는 `http://localhost:8000`에서 실행되므로 포트가 다른 서로 다른 출처가 된다. `CORSMiddleware`를 추가하면 서버가 특정 출처의 요청을 허용하도록 응답 헤더를 설정한다.

개발 단계에서는 사용하는 프론트엔드의 주소만 허용하는 것이 바람직하다. `"*"`(모든 출처 허용)는 편리하지만 보안상 운영 환경에서는 사용하지 않는다. 운영 환경에서는 실제 배포된 프론트엔드 URL만 명시적으로 지정한다.

---

## 4.9 백엔드 의존성 파일 정리

백엔드에 필요한 패키지를 `requirements.txt`에 정리한다.

```
fastapi==0.111.0
uvicorn[standard]==0.30.1
httpx==0.27.0
python-dotenv==1.0.1
pydantic==2.7.4
```

`uvicorn[standard]`의 `[standard]`는 추가 의존성을 포함하는 확장 설치 옵션이다. 스트리밍과 웹소켓 지원에 필요한 패키지가 함께 설치된다.

---

## 4.10 백엔드 Dockerfile 작성

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 파일을 먼저 복사하여 레이어 캐시를 활용한다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드를 복사한다.
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 4.11 로컬에서 백엔드 테스트

Docker 없이 로컬 환경에서 먼저 테스트한다. 가상환경이 활성화된 상태에서 진행한다.

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

서버가 실행되면 브라우저에서 `http://localhost:8000/docs`에 접속한다. Swagger UI에서 `/v1/chat/completions` 엔드포인트를 직접 테스트할 수 있다.

"Try it out" 버튼을 클릭하고 다음과 같이 요청 본문을 입력한 후 "Execute"를 클릭한다.

```json
{
  "model": "HyperCLOVA-X",
  "messages": [
    {"role": "system", "content": "당신은 친절한 AI 어시스턴트입니다."},
    {"role": "user", "content": "안녕하세요. 자기 소개를 해주세요."}
  ],
  "temperature": 0.5,
  "max_tokens": 512,
  "stream": false
}
```

응답이 OpenAI 형식(`choices[0].message.content`)으로 반환되는지 확인한다. 멀티턴 대화를 테스트하려면 응답 메시지를 `messages` 배열에 추가한 뒤 새 질문을 추가하여 다시 요청한다.

```json
{
  "model": "HyperCLOVA-X",
  "messages": [
    {"role": "system", "content": "당신은 친절한 AI 어시스턴트입니다."},
    {"role": "user", "content": "안녕하세요. 자기 소개를 해주세요."},
    {"role": "assistant", "content": "이전 응답 내용..."},
    {"role": "user", "content": "방금 하신 말씀을 요약해 주세요."}
  ],
  "stream": false
}
```

이전 대화 내용을 기억하고 답변한다면 멀티턴 대화가 올바르게 동작하는 것이다.

### 프론트엔드 연동 테스트

백엔드가 정상 동작하면 프론트엔드와 연동하여 실제 채팅을 테스트한다.

**Streamlit(학습용, 포트 8501)**:
1. 백엔드 서버가 포트 8000에서 실행 중인지 확인한다.
2. Streamlit 앱을 실행한다: `streamlit run frontend/app.py`
3. 브라우저에서 `http://localhost:8501`에 접속한다.
4. 채팅창에 메시지를 입력하여 실시간 스트리밍 응답이 표시되는지 확인한다.

**NextChat(운영 대안, 포트 3000)**:
1. 백엔드 서버가 포트 8000에서 실행 중인지 확인한다.
2. `frontend/.env.local`에 `BASE_URL=http://localhost:8000`이 설정되어 있는지 확인한다.
3. NextChat을 실행한다: `cd frontend && npm run dev`
4. 브라우저에서 `http://localhost:3000`에 접속한다.
5. 채팅창에 메시지를 입력하여 실시간 스트리밍 응답이 표시되는지 확인한다.

서버 로그에서 오류가 발생한다면 다음 사항을 먼저 확인한다. `.env` 파일에 API 키가 올바르게 입력되어 있는지, `config.py`에서 환경 변수를 정확히 읽어오고 있는지, CLOVA Studio 대시보드에서 해당 테스트 앱이 활성화되어 있는지를 순서대로 점검한다.

---

## 4.12 API 오류 처리

LLM API를 호출할 때 발생할 수 있는 주요 오류 상황과 대응 방법을 정리한다.

**인증 오류 (401)**는 API 키가 잘못되었거나 만료된 경우 발생한다. `.env` 파일의 키 값이 올바른지, 앞뒤로 불필요한 공백이 없는지 확인한다.

**요청 한도 초과 (429)**는 짧은 시간에 너무 많은 요청을 보낸 경우 발생한다. 요청 사이에 지연을 추가하거나, CLOVA Studio에서 요청 한도를 확인한다.

**서버 오류 (500, 502, 503)**는 API 제공자 측의 문제다. 잠시 후 재시도하거나 CLOVA Studio 서비스 상태 페이지를 확인한다.

**타임아웃**은 LLM이 응답을 생성하는 데 시간이 오래 걸리는 경우 발생한다. `httpx.AsyncClient`의 `timeout` 값을 늘리거나, `maxTokens` 값을 줄여 응답 길이를 제한한다.

`services/llm.py`에 재시도 로직을 추가하면 일시적인 오류에 더 견고하게 대응할 수 있다.

```python
import asyncio

async def generate_with_retry(
    self,
    messages: list[dict],
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> str:
    """오류 발생 시 최대 max_retries번 재시도한다."""
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await self.generate(messages)
        except httpx.HTTPStatusError as e:
            # 클라이언트 오류(4xx)는 재시도해도 의미가 없다.
            if e.response.status_code < 500:
                raise
            last_exception = e
        except (httpx.TimeoutException, httpx.NetworkError) as e:
            last_exception = e

        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay * (attempt + 1))

    raise last_exception
```

---

## 4.13 현재까지의 파일 구조 확인

이 장에서 작성한 파일들을 포함하여 현재 백엔드 프로젝트 구조는 다음과 같다.

```
backend/
├── Dockerfile
├── requirements.txt
├── main.py                      # FastAPI 앱 진입점
├── config.py                    # 설정 관리
├── routers/
│   ├── __init__.py
│   └── chat.py                  # /v1/chat/completions 엔드포인트
├── services/
│   ├── __init__.py
│   ├── llm.py                   # HyperCLOVA X 호출 (교체 대상)
│   └── conversation.py          # 메시지 가공 유틸리티
├── models/
│   ├── __init__.py
│   └── chat.py                  # OpenAI 호환 요청/응답 모델
│
├── .env                         # 실제 API 키 (gitignore)
├── .env.example                 # 환경 변수 템플릿
└── .gitignore
```

모든 파일을 작성한 후 Git에 커밋한다.

```bash
cd backend
git add .
git commit -m "HyperCLOVA X API 연동 백엔드 구현"
```

---

이것으로 제4장의 내용을 마친다. HyperCLOVA X API를 호출하는 백엔드 서버가 완성되었고, Streamlit이나 NextChat 등 OpenAI 호환 프론트엔드와 연동하면 실제로 대화할 수 있는 상태가 되었다. 다음 장에서는 Docker Compose로 전체 서비스를 통합하고 실행 환경을 구성한다.
