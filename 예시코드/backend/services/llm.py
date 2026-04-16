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
