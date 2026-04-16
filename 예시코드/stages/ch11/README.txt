============================================================
  Ch11 스냅샷 — 임베딩 서버 + Ollama/vLLM 인프라
============================================================

이 디렉터리는 chapter11_embedding_server.md까지 완료된 시점의 코드입니다.
ch09에 BGE-M3 임베딩 서버, Ollama/vLLM LLM 서빙 인프라,
5-서비스 Docker Compose 구성을 추가합니다.

가이드 참조: chapter11_embedding_server.md

[ch09 대비 추가/변경 파일]
  deploy/embedding-server/main.py          ← ch11 L306–L484  (BGE-M3 임베딩 서버)
  deploy/embedding-server/requirements.txt ← ch11 L488–L493
  deploy/embedding-server/Dockerfile       ← ch11 L495–L510
  deploy/docker-compose.yml                ← ch11 L587–L713  (5-서비스: +ollama, +embedding-server)
  deploy/.env                              ← ch11 L717–L741  (LLM_PROVIDER, EMBEDDING_PROVIDER 추가)

[ch09에서 그대로 유지되는 파일]
  backend/ (전체 — ch12에서 멀티엔진으로 업데이트됨)
  frontend/ (전체)
  frontend-nextchat/ (전체)
  deploy/docker-compose.dev.yml
  deploy/.env.example (ch12에서 업데이트됨)
