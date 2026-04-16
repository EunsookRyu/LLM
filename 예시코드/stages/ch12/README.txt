============================================================
  Ch12 스냅샷 — 다중 엔진 지원 (CLOVA/Ollama/vLLM)
============================================================

이 디렉터리는 chapter12_multi_engine.md까지 완료된 시점의 코드입니다.
ch11에 LLM 다중 엔진(CLOVA/Ollama/vLLM)과 임베딩 다중 엔진
(CLOVA/로컬 BGE-M3) 지원을 추가합니다.

가이드 참조: chapter12_multi_engine.md

[ch11 대비 추가/변경 파일]
  backend/services/llm.py          ← ch12 L69–L272   (다중 LLM 엔진)
  backend/services/embeddings.py   ← ch12 L318–L495  (다중 임베딩 엔진)
  backend/config.py                ← ch12 L276–L308  (LLM_PROVIDER, EMBEDDING_PROVIDER 추가)
  backend/requirements.txt         ← ch12 L60–L63    (openai 추가)
  backend/reindex_all.py           ← ch12 L507–L604  (전체 재인덱싱 스크립트)
  backend/test_engine_comparison.py ← ch12 L729–L824  (엔진 비교 테스트)

[ch11에서 그대로 유지되는 파일]
  backend/main.py, models/, routers/, 나머지 services/
  backend/test_vector_store.py, test_indexing.py, test_document.txt
  frontend/ (전체)
  frontend-nextchat/ (전체)
  deploy/ (전체 — embedding-server, docker-compose.yml, .env)
