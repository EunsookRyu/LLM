# services/rag_prompt.py
# 가이드 참조: chapter9_rag.md L151–L255


class RAGPromptBuilder:
    """
    RAG 시스템을 위한 프롬프트를 구성하는 클래스.

    프론트엔드가 보낸 OpenAI 호환 메시지 배열에 RAG 컨텍스트를 주입한다.
    프론트엔드 쪽에서는 RAG가 동작하는지 알 수 없다(투명 처리).
    """

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
        if not context:
            return messages

        modified = [msg.copy() for msg in messages]

        context_block = (
            f"\n\n[참고 문서]\n{context}\n\n"
            "위 참고 문서를 바탕으로 사용자의 질문에 답변하세요."
        )

        system_idx = next(
            (i for i, m in enumerate(modified) if m["role"] == "system"),
            None
        )

        if system_idx is not None:
            original_system = modified[system_idx]["content"]
            modified[system_idx]["content"] = (
                f"{self.RAG_INSTRUCTION}\n\n"
                f"[기존 지시사항]\n{original_system}"
                f"{context_block}"
            )
        else:
            modified.insert(0, {
                "role": "system",
                "content": f"{self.RAG_INSTRUCTION}{context_block}"
            })

        return modified

    def build_source_citation(self, results: list[dict]) -> str:
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
