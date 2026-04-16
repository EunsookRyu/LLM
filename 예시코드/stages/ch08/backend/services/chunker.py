# services/chunker.py
# 가이드 참조: chapter8_document_indexing.md L247–L429
from dataclasses import dataclass, field


@dataclass
class TextChunk:
    """
    청킹된 텍스트 조각과 그 메타데이터를 담는 데이터 클래스.
    """
    text: str
    metadata: dict = field(default_factory=dict)


class RecursiveTextChunker:
    """
    재귀적 방식으로 텍스트를 청킹하는 클래스.

    단락(빈 줄) → 줄바꿈 → 문장 부호 → 공백 순서로 분리 기준을 찾는다.
    각 단계에서 청크 크기가 목표 크기를 초과하면 다음 단계로 넘어간다.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        separators: list[str] | None = None
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or [
            "\n\n",   # 단락 구분 (빈 줄)
            "\n",     # 줄바꿈
            ". ",     # 마침표
            "。",     # 한자 마침표
            "? ",     # 물음표
            "! ",     # 느낌표
            ", ",     # 쉼표
            " ",      # 공백
            "",       # 마지막 수단: 문자 단위
        ]

    def chunk(
        self,
        text: str,
        metadata: dict | None = None
    ) -> list[TextChunk]:
        metadata = metadata or {}
        raw_chunks = self._split_text(text, self.separators)

        chunks = []
        for i, chunk_text in enumerate(raw_chunks):
            chunk_metadata = {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(raw_chunks),
            }
            chunks.append(TextChunk(text=chunk_text, metadata=chunk_metadata))

        return chunks

    def chunk_documents(
        self,
        pages: list,  # list[DocumentPage]
    ) -> list[TextChunk]:
        all_chunks = []
        for page in pages:
            page_chunks = self.chunk(page.text, page.metadata)
            all_chunks.extend(page_chunks)
        return all_chunks

    def _split_text(
        self,
        text: str,
        separators: list[str]
    ) -> list[str]:
        if not separators:
            return [text]

        if len(text) <= self.chunk_size:
            return [text]

        separator = separators[0]
        remaining_separators = separators[1:]

        if separator:
            splits = text.split(separator)
        else:
            splits = list(text)

        chunks = []
        current_chunk = ""

        for split in splits:
            candidate = (
                current_chunk + separator + split
                if current_chunk
                else split
            )

            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    if len(current_chunk) > self.chunk_size:
                        sub_chunks = self._split_text(
                            current_chunk, remaining_separators
                        )
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(current_chunk)

                current_chunk = split

        if current_chunk:
            if len(current_chunk) > self.chunk_size:
                sub_chunks = self._split_text(
                    current_chunk, remaining_separators
                )
                chunks.extend(sub_chunks)
            else:
                chunks.append(current_chunk)

        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._apply_overlap(chunks)

        chunks = [c.strip() for c in chunks if len(c.strip()) > 20]

        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            overlap_text = prev_chunk[-self.chunk_overlap:]
            overlapped.append(overlap_text + " " + current_chunk)

        return overlapped


# 기본 청커 인스턴스
default_chunker = RecursiveTextChunker(
    chunk_size=500,
    chunk_overlap=50
)
