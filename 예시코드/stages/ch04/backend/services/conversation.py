# services/conversation.py
# 가이드 참조: chapter4_hyperclovax.md L285–L335
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
    """
    if len(messages) <= max_messages + 1:
        return messages

    system_message = messages[0] if messages[0].get("role") == "system" else None
    recent_messages = messages[-(max_messages):]

    if system_message and recent_messages[0].get("role") != "system":
        return [system_message] + recent_messages
    return recent_messages
