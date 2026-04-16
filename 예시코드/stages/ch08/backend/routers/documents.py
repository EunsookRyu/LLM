# routers/documents.py
# 가이드 참조: chapter8_document_indexing.md L658–L795
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
