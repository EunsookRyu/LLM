# routers/chat.py
# 가이드 참조: chapter4_hyperclovax.md L443–L593
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
    stream=True이면 스트리밍 방식으로, False이면 일반 방식으로 응답한다.
    """
    messages = [m.model_dump() for m in request.messages]
    messages = ensure_system_prompt(messages)
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
    """OpenAI SSE 형식으로 스트리밍 응답을 반환한다."""
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    async def generate():
        try:
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
