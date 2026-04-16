============================================================
  Ch13 스냅샷 — 보안/운영 강화 (최종 버전)
============================================================

이 디렉터리는 chapter13_security_operations.md까지 완료된
프로젝트의 최종 상태입니다.

★ Ch13 스냅샷 = 루트 디렉터리의 최종 코드와 동일합니다.
   별도 파일을 복제하지 않으며, 루트의 코드를 직접 참조하세요.

   ../backend/    ← 최종 백엔드 코드
   ../frontend/   ← 최종 프론트엔드 코드
   ../frontend-nextchat/
   ../deploy/     ← 최종 배포 구성

가이드 참조: chapter13_security_operations.md

[ch12 대비 추가/변경 파일]
  backend/services/auth.py         ← ch13 L56–L193   (API 키 인증 미들웨어)
  backend/services/logger.py       ← ch13 L208–L323  (구조화된 로깅)
  backend/main.py                  ← ch13 L340–L427  (로깅 미들웨어 + 상세 health)
  backend/routers/chat.py          ← ch13 L440–L590  (인증 의존성 추가)
  backend/routers/documents.py     ← ch13 L600–L770  (인증 의존성 추가)
  deploy/docker-compose.prod.yml   ← ch13 L790–L830  (운영 Compose 오버라이드)
  deploy/scripts/backup_qdrant.sh  ← ch13 L859–L905  (Qdrant 백업 스크립트)
  deploy/scripts/health_check.sh   ← ch13 L924–L982  (헬스체크 스크립트)
  deploy/.env                      ← ch13 L850–L858  (API_KEYS, LOG_LEVEL 추가)
  deploy/.env.example              ← ch13 최종 환경변수 예시

[전체 파일 목록은 루트 README.md 참조]
