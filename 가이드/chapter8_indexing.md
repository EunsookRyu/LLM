# 제8장. 문서 인덱싱 파이프라인 구축

## 8.1 이 장의 목표

제7장에서 Qdrant 벡터 데이터베이스와 임베딩 서비스를 준비했다. 이 장에서는 실제 문서 파일을 받아 텍스트를 추출하고, 적절한 크기로 나누고, 임베딩을 생성하여 Qdrant에 저장하는 인덱싱 파이프라인 전체를 구현한다.

이 장을 마치면 내부 업무 문서(PDF, DOCX, TXT)를 시스템에 업로드하면 자동으로 처리되어, 프론트엔드 챗봇이 해당 내용을 참조할 수 있는 상태가 된다.

---

## 8.2 문서 로더 구현

문서 로더는 파일에서 텍스트를 추출하는 역할을 담당한다. 파일 형식마다 텍스트를 추출하는 방법이 다르므로 형식별로 처리 로직을 분리한다.

### 필요한 패키지 설치

```bash
pip install pymupdf python-docx
```

`pymupdf`는 `fitz`라는 이름으로 임포트하며, PDF 파일에서 텍스트를 추출하는 데 사용한다. `python-docx`는 DOCX 파일을 처리한다.

`requirements.txt`에 추가한다.

```
# requirements.txt에 추가
pymupdf==1.24.5
python-docx==1.1.2
```

### 문서 로더 모듈

```python
# services/document_loader.py
import io
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class DocumentPage:
    """
    문서에서 추출한 페이지 단위의 텍스트와 메타데이터를 담는 데이터 클래스.
    청킹 이전의 원본 단위를 표현한다.
    """
    text: str
    metadata: dict = field(default_factory=dict)


class DocumentLoader:
    """
    다양한 파일 형식에서 텍스트를 추출하는 로더 클래스.
    파일 확장자를 기반으로 적절한 처리 방법을 자동으로 선택한다.
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

    def load(self, file_path: str | Path) -> list[DocumentPage]:
        """
        파일 경로를 받아 텍스트를 추출한다.
        파일 형식에 따라 적절한 로더를 자동으로 선택한다.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"지원하지 않는 파일 형식입니다: {extension}\n"
                f"지원 형식: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )

        loader_map = {
            ".pdf": self._load_pdf,
            ".docx": self._load_docx,
            ".txt": self._load_text,
            ".md": self._load_text,
        }

        return loader_map[extension](path)

    def load_from_bytes(
        self,
        file_bytes: bytes,
        filename: str
    ) -> list[DocumentPage]:
        """
        파일 경로 대신 바이트 데이터로 직접 문서를 불러온다.
        API를 통해 파일을 업로드받을 때 사용한다.
        """
        extension = Path(filename).suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"지원하지 않는 파일 형식입니다: {extension}"
            )

        if extension == ".pdf":
            return self._load_pdf_from_bytes(file_bytes, filename)
        elif extension == ".docx":
            return self._load_docx_from_bytes(file_bytes, filename)
        else:
            text = file_bytes.decode("utf-8", errors="replace")
            return [DocumentPage(
                text=text,
                metadata={"source": filename, "page": 1}
            )]

    # ─────────────────────────────────────────────
    # PDF 로더
    # ─────────────────────────────────────────────

    def _load_pdf(self, path: Path) -> list[DocumentPage]:
        with open(path, "rb") as f:
            return self._load_pdf_from_bytes(f.read(), path.name)

    def _load_pdf_from_bytes(
        self,
        file_bytes: bytes,
        filename: str
    ) -> list[DocumentPage]:
        import fitz  # pymupdf

        pages = []
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()

            # 텍스트가 없는 페이지(이미지만 있는 경우 등)는 건너뛴다.
            text = text.strip()
            if not text:
                continue

            pages.append(DocumentPage(
                text=text,
                metadata={
                    "source": filename,
                    "page": page_num + 1,
                    "total_pages": len(doc),
                }
            ))

        doc.close()

        if not pages:
            raise ValueError(
                f"'{filename}'에서 텍스트를 추출할 수 없습니다. "
                "스캔 이미지 PDF이거나 텍스트가 없는 파일일 수 있습니다."
            )

        return pages

    # ─────────────────────────────────────────────
    # DOCX 로더
    # ─────────────────────────────────────────────

    def _load_docx(self, path: Path) -> list[DocumentPage]:
        with open(path, "rb") as f:
            return self._load_docx_from_bytes(f.read(), path.name)

    def _load_docx_from_bytes(
        self,
        file_bytes: bytes,
        filename: str
    ) -> list[DocumentPage]:
        from docx import Document

        doc = Document(io.BytesIO(file_bytes))
        full_text = []

        for paragraph in doc.paragraphs:
            text = paragraph.text.strip()
            if text:
                full_text.append(text)

        # 표 안의 텍스트도 추출한다.
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text = cell.text.strip()
                    if text:
                        full_text.append(text)

        if not full_text:
            raise ValueError(
                f"'{filename}'에서 텍스트를 추출할 수 없습니다."
            )

        # DOCX는 페이지 구분이 불명확하므로 전체를 하나의 페이지로 취급한다.
        return [DocumentPage(
            text="\n".join(full_text),
            metadata={
                "source": filename,
                "page": 1,
                "total_pages": 1,
            }
        )]

    # ─────────────────────────────────────────────
    # 텍스트 로더 (TXT, MD)
    # ─────────────────────────────────────────────

    def _load_text(self, path: Path) -> list[DocumentPage]:
        # 인코딩을 자동으로 감지하여 읽는다.
        # UTF-8을 먼저 시도하고 실패하면 CP949(EUC-KR)로 재시도한다.
        for encoding in ["utf-8", "cp949", "euc-kr"]:
            try:
                text = path.read_text(encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError(
                f"'{path.name}'의 인코딩을 감지하지 못했습니다. "
                "UTF-8 또는 EUC-KR로 저장된 파일인지 확인하세요."
            )

        return [DocumentPage(
            text=text,
            metadata={
                "source": path.name,
                "page": 1,
                "total_pages": 1,
            }
        )]


# 싱글톤 인스턴스
document_loader = DocumentLoader()
```

한국어 문서를 다룰 때는 인코딩 문제가 자주 발생한다. Windows 환경에서 작성된 한글 텍스트 파일은 EUC-KR 또는 CP949 인코딩인 경우가 많다. 위 코드는 UTF-8을 먼저 시도하고 실패하면 CP949로 재시도하여 이 문제에 대응한다. 우리 조직 교육 자료 중 오래된 한글 문서가 CP949로 작성된 경우가 있으므로 이 처리가 특히 중요하다.

---

## 8.3 텍스트 청킹 구현

문서에서 추출한 텍스트를 적절한 크기의 조각으로 나눈다. 제6장에서 설명한 대로 재귀적 청킹 방식을 기본으로 사용한다.

### 청커 모듈

```python
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
```

### 청킹 결과 확인

실제 문서를 청킹했을 때 결과가 어떻게 나오는지 확인하는 것이 중요하다. 청크 크기와 오버랩 설정이 내부 업무 문서의 성격에 맞는지 직접 눈으로 확인한 후 조정한다.

```python
# 청킹 결과 확인 예시
chunker = RecursiveTextChunker(chunk_size=500, chunk_overlap=50)

sample_text = """
1. 연차 휴가 제도
연차 휴가는 근로기준법 제60조에 따라 1년간 80% 이상 출근한 근로자에게 부여된다.
연소실에서 추진제가 연소되면 고온 고압의 가스가 생성되고, 이 가스가 노즐을 통해
1년 미만 근무 시 매월 1일의 유급휴가가 발생하며, 1년 이상 근무 시 15일의 연차가 부여된다.

2. 추진제의 종류
추진제는 크게 고체 추진제와 액체 추진제로 나뉜다.
고체 추진제는 구조가 간단하고 보관이 용이하며, 한국형 발사체 나로호의 1단에도 사용되었다.
미사용 연차에 대해서는 연차수당으로 보상받을 수 있으며, 연차 촉진 제도를 통해 사용을 권장한다.

3. 단 분리 기술
경조사 휴가는 결혼, 출산, 사망 등의 경조사 발생 시 부여되는 유급휴가이다.
경조사 종류에 따라 본인 결혼 5일, 자녀 결혼 1일, 배우자 출산 10일 등의 휴가가 부여된다.
"""

chunks = chunker.chunk(sample_text)
for i, chunk in enumerate(chunks):
    print(f"청크 {i+1} (길이: {len(chunk.text)}자)")
    print(chunk.text)
    print("---")
```

---

## 8.4 인덱싱 파이프라인 통합

문서 로더, 청커, 임베딩 서비스, 벡터 저장소를 하나로 연결하는 인덱싱 파이프라인을 구현한다.

```python
# services/indexer.py
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
        """
        파일 경로로부터 문서를 인덱싱한다.

        반환값:
        {
            "source": 파일명,
            "pages": 처리된 페이지 수,
            "chunks": 생성된 청크 수,
            "indexed": 저장된 벡터 수,
        }
        """
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
        """
        파일 바이트 데이터로부터 문서를 인덱싱한다.
        API를 통해 파일을 업로드받을 때 사용한다.
        """
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
        """
        추출된 페이지를 청킹 → 임베딩 → 저장 단계로 처리한다.
        """
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

        # 각 청크의 메타데이터를 구성한다.
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
        """
        이미 인덱싱된 파일을 다시 인덱싱한다.
        기존 데이터를 먼저 삭제하고 새로 저장한다.
        """
        path = Path(file_path)
        source_name = path.name

        print(f"[재인덱싱] 기존 데이터 삭제 중: {source_name}")
        self.vector_svc.delete_by_source(source_name)

        return await self.index_file(file_path, extra_metadata)

    def get_indexed_sources(self) -> dict:
        """현재 인덱싱된 컬렉션 정보를 반환한다."""
        return self.vector_svc.get_collection_info()


# 싱글톤 인스턴스
indexing_pipeline = IndexingPipeline()
```

---

## 8.5 문서 관리 API 엔드포인트

관리자가 내부 업무 문서를 업로드하고 관리할 수 있는 API 엔드포인트를 추가한다. 이 엔드포인트는 프론트엔드 챗봇 인터페이스와는 별도로, 관리자가 Swagger UI나 curl을 통해 직접 호출하는 관리용 API이다.

### 데이터 모델

```python
# models/document.py
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    """문서 업로드 성공 응답"""
    source: str = Field(..., description="업로드된 파일 이름")
    pages: int = Field(..., description="처리된 페이지 수")
    chunks: int = Field(..., description="생성된 청크 수")
    indexed: int = Field(..., description="저장된 벡터 수")
    message: str = "문서가 성공적으로 인덱싱되었습니다."


class DocumentDeleteRequest(BaseModel):
    """문서 삭제 요청"""
    source: str = Field(..., description="삭제할 파일 이름")


class DocumentDeleteResponse(BaseModel):
    """문서 삭제 응답"""
    source: str
    message: str = "문서가 삭제되었습니다."


class CollectionInfoResponse(BaseModel):
    """컬렉션 정보 응답"""
    name: str
    points_count: int
    vector_size: int
```

### 문서 라우터

```python
# routers/documents.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from models.document import (
    DocumentUploadResponse,
    DocumentDeleteRequest,
    DocumentDeleteResponse,
    CollectionInfoResponse,
)
from services.indexer import indexing_pipeline
from services.vector_store import vector_store

router = APIRouter(prefix="/documents", tags=["documents"])

# 허용하는 파일 확장자
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}

# 최대 파일 크기 (50MB)
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    문서 파일을 업로드하고 인덱싱한다.
    지원 형식: PDF, DOCX, TXT, MD
    """
    # 파일 확장자 확인
    filename = file.filename or ""
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"지원하지 않는 파일 형식입니다: '{extension}'\n"
                f"지원 형식: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        )

    # 파일 크기 확인
    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=(
                f"파일 크기가 허용 한도를 초과했습니다. "
                f"최대 {MAX_FILE_SIZE // (1024 * 1024)}MB까지 허용됩니다."
            )
        )

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="빈 파일은 업로드할 수 없습니다."
        )

    # 인덱싱 실행
    try:
        result = await indexing_pipeline.index_bytes(
            file_bytes=file_bytes,
            filename=filename
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"인덱싱 중 오류가 발생했습니다: {str(e)}"
        )

    return DocumentUploadResponse(**result)


@router.post("/reupload", response_model=DocumentUploadResponse)
async def reupload_document(file: UploadFile = File(...)):
    """
    이미 인덱싱된 문서를 새 버전으로 교체한다.
    같은 파일 이름의 기존 데이터를 삭제하고 다시 인덱싱한다.
    """
    filename = file.filename or ""
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다: '{extension}'"
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")

    # 기존 데이터 삭제 후 재인덱싱
    vector_store.delete_by_source(filename)

    try:
        result = await indexing_pipeline.index_bytes(
            file_bytes=file_bytes,
            filename=filename
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"재인덱싱 중 오류가 발생했습니다: {str(e)}"
        )

    return DocumentUploadResponse(
        **result,
        message="문서가 성공적으로 교체되었습니다."
    )


@router.delete("/delete", response_model=DocumentDeleteResponse)
async def delete_document(request: DocumentDeleteRequest):
    """
    인덱싱된 문서를 삭제한다.
    해당 파일에서 생성된 모든 청크가 Qdrant에서 제거된다.
    """
    try:
        vector_store.delete_by_source(request.source)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"문서 삭제 중 오류가 발생했습니다: {str(e)}"
        )

    return DocumentDeleteResponse(source=request.source)


@router.get("/info", response_model=CollectionInfoResponse)
async def get_collection_info():
    """현재 인덱싱된 documents 컬렉션의 상태 정보를 반환한다."""
    info = vector_store.get_collection_info()
    return CollectionInfoResponse(**info)
```

### main.py에 문서 라우터 등록

```python
# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, documents   # documents 추가

app = FastAPI(
    title="내부 문서 AI 챗봇 API",
    description="HyperCLOVA X 기반 내부 업무 RAG 챗봇 API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(documents.router)   # 추가


@app.get("/")
async def root():
    return {"status": "ok", "message": "내부 문서 AI 챗봇 API가 실행 중입니다."}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

## 8.6 인덱싱 파이프라인 동작 확인

전체 파이프라인이 정상적으로 동작하는지 확인한다. 먼저 간단한 테스트용 내부 업무 문서를 만든다.

```bash
# 테스트 문서 생성
cat > test_document.txt << 'EOF'
1. 연차 휴가 제도
연차 휴가는 근로기준법 제60조에 따라 1년간 80% 이상 출근한 근로자에게 부여된다.
연소실에서 추진제가 연소되면 고온 고압의 가스가 생성되고, 이 가스가 노즐을 통해
1년 미만 근무 시 매월 1일의 유급휴가가 발생하며, 1년 이상 근무 시 15일의 연차가 부여된다.

2. 출장비 정산 규정
출장비는 교통비, 숙박비, 식비, 일비로 구분하여 정산한다.
교통비는 실비 정산을 원칙으로 하며, 대중교통 이용을 우선한다.
정지궤도(GEO)는 고도 약 36,000km로, 통신 위성과 기상 위성에 주로 사용된다.

3. 정보보안 관리 규정
정보보안은 조직의 핵심 자산을 보호하기 위한 필수 관리 체계이다.
3단 구성으로, 1단에 75톤급 액체 엔진 4기, 2단에 75톤급 1기, 3단에 7톤급 1기를 탑재한다.
2022년 6월 두 번째 발사에서 성공적으로 위성을 궤도에 투입하였다.

4. 비품 구매 및 관리
비품 구매는 소속 부서에서 필요한 물품을 총무팀에 요청하는 절차로 진행된다.
온도는 햇빛이 닿는 면과 그늘진 면의 차이가 수백 도에 달한다.
10만원 이상의 비품은 자산으로 등록하여 관리하며, 연 1회 실사를 실시한다.
EOF
```

테스트 스크립트를 작성한다.

```python
# test_indexing.py
import asyncio
from services.indexer import indexing_pipeline
from services.embeddings import embedding_service
from services.vector_store import vector_store


async def test():
    # 1. 문서 인덱싱
    print("=== 문서 인덱싱 테스트 ===")
    result = await indexing_pipeline.index_file("test_document.txt")
    print(f"결과: {result}")

    # 2. 인덱싱된 벡터 수 확인
    print("\n=== 컬렉션 정보 ===")
    info = vector_store.get_collection_info()
    print(info)

    # 3. 검색 테스트
    print("\n=== 검색 테스트 ===")
    queries = [
        "연차 휴가 신청 절차가 어떻게 되나요?",
        "출장비 정산 기한은 어떻게 되나요?",
        "재택근무 신청 방법을 알려주세요.",
    ]

    for query in queries:
        print(f"\n질문: {query}")
        query_embedding = await embedding_service.embed(query)
        results = vector_store.search(query_embedding, top_k=2)
        for i, result in enumerate(results):
            print(f"  결과 {i+1} (점수: {result['score']:.4f}): {result['text'][:80]}...")


if __name__ == "__main__":
    asyncio.run(test())
```

Qdrant 컨테이너가 실행 중인지 확인하고 테스트를 실행한다.

```bash
# Qdrant 실행 확인
docker ps | grep qdrant

# 테스트 실행
python test_indexing.py
```

검색 결과에서 각 질문과 관련성 높은 내용이 상위에 나타나는지 확인한다. "연차 휴가 신청 절차가 어떻게 되나요?" 질문에 근로기준법 관련 내용이, "출장비 정산 기한은 어떻게 되나요?" 질문에 정산 기한 관련 내용이 나타난다면 파이프라인이 정상 동작하는 것이다.

---

## 8.7 문서 업로드 및 관리 방법

이 시스템에서 프론트엔드(Streamlit 또는 NextChat)는 채팅 전용 인터페이스다. 문서 업로드 UI가 포함되어 있지 않으므로, **문서 인덱싱은 Swagger UI 또는 curl을 통해서만 수행한다.** 이것이 운영 환경에서의 유일한 문서 관리 경로이므로, 아래 방법을 숙지해 두어야 한다.

### Swagger UI로 업로드 (브라우저)

서버를 실행하고 `http://localhost:8000/docs`에서 Swagger UI를 열어 문서 업로드 API를 사용한다.

```bash
uvicorn main:app --reload --port 8000
```

`/documents/upload` 엔드포인트에서 "Try it out"을 클릭하고 파일을 선택하여 업로드한다. 응답으로 처리된 페이지 수, 청크 수, 저장된 벡터 수가 반환된다.

### curl로 업로드 (터미널)

스크립트 자동화나 서버 직접 접근이 필요한 경우에는 `curl`을 사용한다.

```bash
curl -X POST "http://localhost:8000/documents/upload" \
  -H "accept: application/json" \
  -F "file=@test_document.txt"
```

여러 파일을 한 번에 등록해야 한다면 루프로 처리할 수 있다.

```bash
# documents/ 폴더의 모든 PDF를 순서대로 업로드
for f in documents/*.pdf; do
  echo "업로드 중: $f"
  curl -s -X POST "http://localhost:8000/documents/upload" \
    -F "file=@${f}" | python3 -m json.tool
  sleep 1   # API 호출 간격을 두어 임베딩 API 요청 한도 초과 방지
done
```

정상 응답 예시는 다음과 같다.

```json
{
  "source": "test_document.txt",
  "pages": 1,
  "chunks": 4,
  "indexed": 4,
  "message": "문서가 성공적으로 인덱싱되었습니다."
}
```

> **운영 환경 접근**: 13장에서 API 인증을 추가하면 curl 요청에 `-H "X-API-Key: 발급키"` 헤더를 포함해야 한다. Swagger UI에서도 우측 상단 "Authorize" 버튼으로 키를 등록한 뒤 사용한다.

---

## 8.8 대용량 문서 처리 시 주의사항

실무에서는 수백 페이지에 달하는 업무 매뉴얼 PDF를 처리해야 하는 경우가 있다. 이 경우 몇 가지 사항을 추가로 고려해야 한다.

### 임베딩 API 요청 한도

HyperCLOVA X 임베딩 API(`clir-sts-dolphin`)를 사용하는 경우, 분당 허용 요청 수에 제한이 있다. 수백 개의 청크를 한꺼번에 임베딩하면 이 한도를 초과할 수 있다. `embed_batch` 메서드에서 배치 사이 대기 시간(`asyncio.sleep`)을 조정하여 이를 방지한다.

### 업로드 요청 타임아웃

FastAPI와 uvicorn의 기본 요청 타임아웃이 대용량 파일 처리 시간보다 짧을 수 있다. 대용량 파일 처리는 백그라운드 태스크로 분리하는 것이 이상적이지만, 이 가이드의 범위를 벗어나므로 일단 타임아웃 값을 늘리는 방식으로 대응한다. `uvicorn` 실행 시 `--timeout-keep-alive` 옵션을 조정하거나, nginx 리버스 프록시를 사용하는 경우 `proxy_read_timeout` 값을 늘린다.

### 메모리 사용량

매우 큰 파일은 바이트 데이터를 메모리에 올리는 것만으로도 서버 메모리에 부담을 줄 수 있다. 운영 환경에서는 파일을 임시 디스크에 저장하고 처리하는 방식을 고려한다.

---

## 8.9 현재까지의 파일 구조

```
backend/
├── .dockerignore
├── Dockerfile
├── requirements.txt
├── main.py
├── config.py
├── test_vector_store.py
├── test_indexing.py             # 인덱싱 파이프라인 테스트
├── test_document.txt            # 테스트용 샘플 문서
├── routers/
│   ├── __init__.py
│   ├── chat.py
│   └── documents.py             # 문서 관리 API
├── services/
│   ├── __init__.py
│   ├── llm.py
│   ├── embeddings.py
│   ├── vector_store.py
│   ├── document_loader.py       # 문서 로더
│   ├── chunker.py               # 텍스트 청커
│   └── indexer.py               # 인덱싱 파이프라인
└── models/
    ├── __init__.py
    ├── chat.py
    └── document.py              # 문서 관련 데이터 모델
```

프론트엔드(`frontend`)와 배포 설정(`deploy`)은 별도 저장소이므로 여기에는 백엔드 구조만 나타낸다. 전체 서비스 구성은 제5장의 Docker Compose 설정을 참고한다.

변경 사항을 커밋한다.

```bash
git add .
git commit -m "feat: 문서 인덱싱 파이프라인 및 문서 관리 API 구현

- 문서 로더: PDF, DOCX, TXT, MD 지원 (CP949 인코딩 대응)
- 재귀적 텍스트 청커: 500자 청크, 50자 오버랩
- 인덱싱 파이프라인: 추출 → 청킹 → 임베딩 → Qdrant 저장
- 문서 관리 API: 업로드, 교체, 삭제, 컬렉션 정보 조회"
```

---

이것으로 제8장의 내용을 마친다. 문서를 불러오고, 나누고, 임베딩하여 Qdrant의 `documents` 컬렉션에 저장하는 인덱싱 파이프라인 전체가 완성되었다. 다음 장에서는 이 파이프라인을 프론트엔드 챗봇과 연결하여, 사용자의 질문에 관련 교육 자료를 검색하고 그 내용을 바탕으로 답변하는 RAG 기능을 `/v1/chat/completions` 엔드포인트에 통합한다.
