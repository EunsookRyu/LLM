# services/chunker.py
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
        """
        chunk_size: 청크의 최대 문자 수
        chunk_overlap: 인접 청크 사이의 겹치는 문자 수
        separators: 텍스트를 나눌 구분자 목록 (우선순위 순서)
        """
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
        """
        텍스트를 청크 목록으로 분리한다.
        메타데이터는 모든 청크에 복사된다.
        """
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
        """
        여러 페이지로 구성된 문서를 청킹한다.
        각 페이지를 독립적으로 청킹하고 결과를 합친다.
        페이지 메타데이터는 각 청크에 유지된다.
        """
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
        """
        텍스트를 재귀적으로 분리한다.
        현재 구분자로 나눈 결과가 chunk_size를 초과하면
        다음 구분자로 재귀 호출한다.
        """
        # 사용 가능한 구분자가 없거나 텍스트가 충분히 작으면 그대로 반환한다.
        if not separators:
            return [text]

        if len(text) <= self.chunk_size:
            return [text]

        separator = separators[0]
        remaining_separators = separators[1:]

        # 현재 구분자로 텍스트를 나눈다.
        if separator:
            splits = text.split(separator)
        else:
            # 빈 문자열 구분자는 문자 단위로 분리한다.
            splits = list(text)

        # 나눈 조각들을 chunk_size에 맞게 병합한다.
        chunks = []
        current_chunk = ""

        for split in splits:
            # 구분자를 다시 붙여 원본 텍스트 구조를 유지한다.
            candidate = (
                current_chunk + separator + split
                if current_chunk
                else split
            )

            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
            else:
                # 현재 청크를 저장하고 새 청크를 시작한다.
                if current_chunk:
                    # 현재 청크가 chunk_size를 초과한다면 재귀적으로 더 나눈다.
                    if len(current_chunk) > self.chunk_size:
                        sub_chunks = self._split_text(
                            current_chunk, remaining_separators
                        )
                        chunks.extend(sub_chunks)
                    else:
                        chunks.append(current_chunk)

                current_chunk = split

        # 마지막 청크 처리
        if current_chunk:
            if len(current_chunk) > self.chunk_size:
                sub_chunks = self._split_text(
                    current_chunk, remaining_separators
                )
                chunks.extend(sub_chunks)
            else:
                chunks.append(current_chunk)

        # 오버랩 적용
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._apply_overlap(chunks)

        # 너무 짧은 청크(노이즈)는 제거한다.
        chunks = [c.strip() for c in chunks if len(c.strip()) > 20]

        return chunks

    def _apply_overlap(self, chunks: list[str]) -> list[str]:
        """
        인접한 청크 사이에 오버랩을 적용한다.
        각 청크의 끝부분을 다음 청크의 시작에 붙인다.
        """
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # 이전 청크의 마지막 chunk_overlap 문자를 현재 청크 앞에 붙인다.
            overlap_text = prev_chunk[-self.chunk_overlap:]
            overlapped.append(overlap_text + " " + current_chunk)

        return overlapped


# 기본 청커 인스턴스
# chunk_size와 chunk_overlap은 문서 특성에 따라 조정할 수 있다.
default_chunker = RecursiveTextChunker(
    chunk_size=500,
    chunk_overlap=50
)
