============================================================
  Ch07 스냅샷 — Qdrant 벡터 데이터베이스 + 임베딩
============================================================

이 디렉터리는 chapter7_qdrant.md까지 완료된 시점의 코드입니다.
ch05의 프로젝트에 임베딩 서비스, 벡터 저장소 서비스, 테스트 스크립트를
추가하고, config.py와 requirements.txt를 확장합니다.

가이드 참조: chapter7_qdrant.md

[ch05 대비 추가/변경 파일]
  backend/services/embeddings.py   ← ch7 L293–L367  (HyperCLOVA X 임베딩, CLOVA 전용)
  backend/services/vector_store.py ← ch7 L384–L547  (Qdrant 벡터 저장소)
  backend/config.py                ← ch7 L373–L376, L551–L556  (config 확장)
  backend/requirements.txt         ← ch7 L735–L743  (qdrant-client 추가)
  backend/test_vector_store.py     ← ch7 L574–L635  (통합 테스트)
  deploy/.env                      ← ch7 L560–L564  (QDRANT 환경변수 추가)
  deploy/.env.example              ← ch7 L690–L702  (환경변수 예시 확장)

[ch05에서 그대로 유지되는 파일]
  backend/main.py
  backend/models/chat.py
  backend/routers/chat.py
  backend/services/llm.py
  backend/services/conversation.py
  backend/Dockerfile
  backend/.dockerignore
  frontend/app.py
  frontend/requirements.txt, .env, Dockerfile, .dockerignore
  frontend-nextchat/.env.local, Dockerfile, .dockerignore
  deploy/docker-compose.yml (backend env에 QDRANT 변수 추가 — L677–L686)
  deploy/docker-compose.dev.yml
