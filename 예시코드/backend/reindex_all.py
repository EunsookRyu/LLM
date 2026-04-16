# reindex_all.py
"""
임베딩 모델 교체 후 모든 문서를 재인덱싱하는 스크립트.

실행 전 확인사항:
1. EMBEDDING_PROVIDER가 새 모델로 변경되어 있는지 확인한다.
2. 기존 내부 업무 문서 파일이 모두 보관되어 있는지 확인한다.
3. Qdrant와 임베딩 서버가 실행 중인지 확인한다.

주의: 이 스크립트를 실행하면 documents 컬렉션의 기존 벡터 데이터가
      모두 삭제된다.
"""

import asyncio
import sys
from pathlib import Path

from services.vector_store import vector_store
from services.indexer import indexing_pipeline


DOCUMENTS_DIR = Path("./documents")  # 재인덱싱할 문서가 저장된 폴더


async def reindex_all():
    print("=" * 60)
    print("documents 컬렉션 전체 재인덱싱 시작")
    print("=" * 60)

    # 문서 폴더 확인
    if not DOCUMENTS_DIR.exists():
        print(f"오류: 문서 폴더를 찾을 수 없습니다: {DOCUMENTS_DIR}")
        print("내부 업무 문서가 저장된 폴더 경로를 DOCUMENTS_DIR에 설정하세요.")
        sys.exit(1)

    document_files = list(DOCUMENTS_DIR.glob("**/*"))
    document_files = [
        f for f in document_files
        if f.is_file() and f.suffix.lower() in {".pdf", ".docx", ".txt", ".md"}
    ]

    if not document_files:
        print("인덱싱할 문서 파일이 없습니다.")
        sys.exit(0)

    print(f"발견된 문서: {len(document_files)}개")
    for f in document_files:
        print(f"  - {f.name}")

    # 사용자 확인
    print("\n경고: documents 컬렉션의 모든 벡터 데이터가 삭제됩니다.")
    confirm = input("계속 진행하려면 'yes'를 입력하세요: ")
    if confirm.strip().lower() != "yes":
        print("취소되었습니다.")
        sys.exit(0)

    # 기존 컬렉션 데이터 삭제
    print("\n기존 컬렉션 데이터 삭제 중...")
    client = vector_store.client
    collection_name = vector_store.collection_name
    client.delete_collection(collection_name)
    vector_store._ensure_collection()
    print("컬렉션 초기화 완료")

    # 모든 문서 재인덱싱
    results = []
    failed = []

    for i, file_path in enumerate(document_files):
        print(f"\n[{i + 1}/{len(document_files)}] {file_path.name}")
        try:
            result = await indexing_pipeline.index_file(file_path)
            results.append(result)
        except Exception as e:
            print(f"  오류 발생: {str(e)}")
            failed.append({"file": file_path.name, "error": str(e)})

    # 결과 요약
    print("\n" + "=" * 60)
    print("재인덱싱 완료")
    print("=" * 60)
    print(f"성공: {len(results)}개 파일")
    total_chunks = sum(r["chunks"] for r in results)
    print(f"총 저장된 벡터: {total_chunks}개")

    if failed:
        print(f"\n실패: {len(failed)}개 파일")
        for f in failed:
            print(f"  - {f['file']}: {f['error']}")

    info = vector_store.get_collection_info()
    print(f"\n최종 컬렉션 상태: {info['points_count']}개 벡터 저장됨")


if __name__ == "__main__":
    asyncio.run(reindex_all())
