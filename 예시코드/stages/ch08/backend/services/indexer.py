# services/indexer.py
# 가이드 참조: chapter8_document_indexing.md L468–L614
from pathlib import Path

from services.document_loader import document_loader, DocumentPage
from services.chunker import default_chunker
from services.embeddings import embedding_service
from services.vector_store import vector_store


class IndexingPipeline:
    """
    문서 파일을 받아 텍스트 추출 → 청킹 → 임베딩 → 저장 단계를
    순서대로 실행하는 인덱싱 파이프라인.
    """

    def __init__(self):
        self.loader = document_loader
        self.chunker = default_chunker
        self.embedding_svc = embedding_service
        self.vector_svc = vector_store

    async def index_file(
        self,
        file_path: str | Path,
        extra_metadata: dict | None = None
    ) -> dict:
        path = Path(file_path)
        print(f"[인덱싱 시작] {path.name}")

        # 1단계: 텍스트 추출
        print("  1/4 텍스트 추출 중...")
        pages = self.loader.load(path)
        print(f"      {len(pages)}개 페이지 추출 완료")

        return await self._process_pages(
            pages=pages,
            source_name=path.name,
            extra_metadata=extra_metadata
        )

    async def index_bytes(
        self,
        file_bytes: bytes,
        filename: str,
        extra_metadata: dict | None = None
    ) -> dict:
        print(f"[인덱싱 시작] {filename}")

        # 1단계: 텍스트 추출
        print("  1/4 텍스트 추출 중...")
        pages = self.loader.load_from_bytes(file_bytes, filename)
        print(f"      {len(pages)}개 페이지 추출 완료")

        return await self._process_pages(
            pages=pages,
            source_name=filename,
            extra_metadata=extra_metadata
        )

    async def _process_pages(
        self,
        pages: list[DocumentPage],
        source_name: str,
        extra_metadata: dict | None = None
    ) -> dict:
        # 2단계: 청킹
        print("  2/4 청킹 중...")
        chunks = self.chunker.chunk_documents(pages)
        print(f"      {len(chunks)}개 청크 생성 완료")

        if not chunks:
            raise ValueError(
                f"'{source_name}'에서 유효한 텍스트 청크를 생성하지 못했습니다."
            )

        # 3단계: 임베딩 생성
        print("  3/4 임베딩 생성 중...")
        texts = [chunk.text for chunk in chunks]
        embeddings = await self.embedding_svc.embed_batch(texts)
        print(f"      {len(embeddings)}개 임베딩 생성 완료")

        # 4단계: Qdrant에 저장
        print("  4/4 Qdrant에 저장 중...")

        metadatas = []
        for chunk in chunks:
            metadata = {**chunk.metadata}
            if extra_metadata:
                metadata.update(extra_metadata)
            metadatas.append(metadata)

        ids = self.vector_svc.add_documents(texts, embeddings, metadatas)
        print(f"      {len(ids)}개 벡터 저장 완료")
        print(f"[인덱싱 완료] {source_name}")

        return {
            "source": source_name,
            "pages": len(pages),
            "chunks": len(chunks),
            "indexed": len(ids),
        }

    async def reindex_file(
        self,
        file_path: str | Path,
        extra_metadata: dict | None = None
    ) -> dict:
        path = Path(file_path)
        source_name = path.name

        print(f"[재인덱싱] 기존 데이터 삭제 중: {source_name}")
        self.vector_svc.delete_by_source(source_name)

        return await self.index_file(file_path, extra_metadata)

    def get_indexed_sources(self) -> dict:
        return self.vector_svc.get_collection_info()


# 싱글톤 인스턴스
indexing_pipeline = IndexingPipeline()
