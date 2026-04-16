#!/bin/bash
# backup_qdrant.sh
# 크론탭에 등록하여 매일 자동으로 실행한다.

BACKUP_DIR="${HOME}/chatbot-backups/qdrant"
COLLECTION="documents"
DATE=$(date '+%Y%m%d_%H%M%S')

# 운영 환경에서는 Qdrant 포트가 외부에 노출되지 않으므로
# docker exec를 통해 컨테이너 내부에서 API를 호출한다.
# 포트가 노출된 개발 환경에서는 localhost:6333을 직접 사용한다.
if docker ps --filter "name=chatbot-qdrant" --format "{{.Names}}" | grep -q chatbot-qdrant; then
    USE_DOCKER_EXEC=true
    QDRANT_INTERNAL="http://localhost:6333"
    QDRANT_URL="http://localhost:6333"  # 파일 다운로드용 (포트 노출 여부에 따라)
else
    USE_DOCKER_EXEC=false
    QDRANT_URL="http://localhost:6333"
fi
BACKUP_FILE="${BACKUP_DIR}/${COLLECTION}_${DATE}.snapshot"
KEEP_DAYS=7   # 7일치 백업 보관

mkdir -p "${BACKUP_DIR}"

echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | Qdrant 백업 시작"

# 스냅샷 생성 (운영 환경은 docker exec 사용)
if [ "$USE_DOCKER_EXEC" = true ]; then
    snapshot_response=$(docker exec chatbot-qdrant \
      curl -s -X POST "${QDRANT_INTERNAL}/collections/${COLLECTION}/snapshots")
else
    snapshot_response=$(curl -s -X POST \
      "${QDRANT_URL}/collections/${COLLECTION}/snapshots")
fi

snapshot_name=$(echo "$snapshot_response" | python3 -c \
  "import sys,json; print(json.load(sys.stdin)['result']['name'])")

if [ -z "$snapshot_name" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR | 스냅샷 생성 실패"
    exit 1
fi

# 스냅샷 파일 다운로드
curl -s -o "${BACKUP_FILE}" \
  "${QDRANT_URL}/collections/${COLLECTION}/snapshots/${snapshot_name}"

if [ $? -eq 0 ]; then
    size=$(du -sh "${BACKUP_FILE}" | cut -f1)
    echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | 백업 완료: ${BACKUP_FILE} (${size})"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR | 백업 파일 다운로드 실패"
    exit 1
fi

# 서버에서 스냅샷 삭제 (디스크 절약)
curl -s -X DELETE \
  "${QDRANT_URL}/collections/${COLLECTION}/snapshots/${snapshot_name}" \
  > /dev/null

# 오래된 백업 삭제
find "${BACKUP_DIR}" -name "*.snapshot" -mtime "+${KEEP_DAYS}" -delete
echo "$(date '+%Y-%m-%d %H:%M:%S') | INFO | ${KEEP_DAYS}일 이전 백업 삭제 완료"
