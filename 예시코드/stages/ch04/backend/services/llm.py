# services/llm.py
# 가이드 참조: chapter4_hyperclovax.md L148–L257
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
llm_service = HyperClovaXService()
