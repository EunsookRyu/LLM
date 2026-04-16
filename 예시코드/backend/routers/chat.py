# routers/chat.py
import json
import time
import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse, JSONResponse

from auth import verify_api_key
from models.chat import ChatCompletionRequest
from services.llm import llm_service
from services.retriever import retriever
from services.rag_prompt import rag_prompt_builder

router = APIRouter(tags=["chat"], dependencies=[Depends(verify_api_key)])


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
