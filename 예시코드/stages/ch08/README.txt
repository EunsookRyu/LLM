============================================================
  Ch08 스냅샷 — 문서 인덱싱 파이프라인
============================================================

이 디렉터리는 chapter8_document_indexing.md까지 완료된 시점의 코드입니다.
ch07에 문서 로더, 청커, 인덱싱 파이프라인, 문서 관리 API를 추가합니다.

가이드 참조: chapter8_document_indexing.md

[ch07 대비 추가/변경 파일]
  backend/services/document_loader.py ← ch8 L33–L235   (PDF/DOCX/TXT 텍스트 추출)
  backend/services/chunker.py         ← ch8 L247–L429  (재귀적 텍스트 청킹)
  backend/services/indexer.py         ← ch8 L468–L614  (인덱싱 파이프라인)
  backend/models/document.py          ← ch8 L624–L654  (문서 API 모델)
  backend/routers/documents.py        ← ch8 L658–L795  (문서 업로드/삭제 라우터)
  backend/main.py                     ← ch8 L799–L831  (documents 라우터 등록)
  backend/test_indexing.py            ← ch8 L866–L903  (인덱싱 통합 테스트)
  backend/test_document.txt           ← ch8 L839–L862  (샘플 테스트 문서)

[ch07에서 그대로 유지되는 파일]
  backend/config.py
  backend/models/chat.py
  backend/routers/chat.py
  backend/services/llm.py
  backend/services/conversation.py
  backend/services/embeddings.py
  backend/services/vector_store.py
  backend/requirements.txt
  backend/Dockerfile, .dockerignore
  frontend/ (전체)
  frontend-nextchat/ (전체)
  deploy/ (전체)
