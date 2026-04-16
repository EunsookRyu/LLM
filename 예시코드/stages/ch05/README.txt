============================================================
  Ch05 스냅샷 — Streamlit 프론트엔드 + Docker Compose 배포
============================================================

이 디렉터리는 chapter5_streamlit.md까지 완료된 시점의 코드입니다.
ch04의 백엔드에 Streamlit 프론트엔드, NextChat 대안 프론트엔드,
Docker Compose 기반 배포 구성을 추가합니다.

가이드 참조: chapter5_streamlit.md

[ch04 대비 추가/변경 파일]
  frontend/app.py              ← ch5 L30–L81   (Streamlit 채팅 UI)
  frontend/requirements.txt    ← ch5 L95–L99
  frontend/.env                ← ch5 L105–L108
  frontend/Dockerfile          ← ch5 L157–L173
  frontend/.dockerignore       ← ch5 L187–L197
  frontend-nextchat/.env.local ← ch5 L137–L145
  frontend-nextchat/Dockerfile ← ch5 L203–L232
  frontend-nextchat/.dockerignore ← ch5 L240–L247
  deploy/docker-compose.yml    ← ch5 L264–L340  (3-service: frontend+backend+qdrant)
  deploy/docker-compose.dev.yml ← ch5 L533–L549
  deploy/.env                  ← ch5 L406–L412
  deploy/.env.example          ← ch5 L416–L422
  backend/.dockerignore        ← ch5 L466–L477

[ch04에서 그대로 유지되는 파일]
  backend/config.py
  backend/main.py
  backend/models/chat.py
  backend/routers/chat.py
  backend/services/llm.py
  backend/services/conversation.py
  backend/requirements.txt
  backend/Dockerfile
