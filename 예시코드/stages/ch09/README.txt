============================================================
  Ch09 스냅샷 — RAG 파이프라인 통합
============================================================

이 디렉터리는 chapter9_rag.md까지 완료된 시점의 코드입니다.
ch08에 RAG 검색기, 프롬프트 빌더를 추가하고, chat 라우터를
RAG 통합 버전으로 업데이트합니다.

가이드 참조: chapter9_rag.md

[ch08 대비 추가/변경 파일]
  backend/services/retriever.py    ← ch9 L19–L139   (Qdrant 벡터 검색 + 중복 제거)
  backend/services/rag_prompt.py   ← ch9 L151–L255  (RAG 프롬프트 투명 주입)
  backend/routers/chat.py          ← ch9 L278–L415  (RAG 통합 /v1/chat/completions)

[ch08에서 그대로 유지되는 파일]
  backend/config.py, main.py, requirements.txt, Dockerfile, .dockerignore
  backend/models/chat.py, document.py
  backend/routers/documents.py
  backend/services/llm.py, conversation.py, embeddings.py
  backend/services/vector_store.py, document_loader.py, chunker.py, indexer.py
  backend/test_vector_store.py, test_indexing.py, test_document.txt
  frontend/ (전체)
  frontend-nextchat/ (전체)
  deploy/ (전체)
