#!/bin/bash
# backup_config.sh

BACKUP_DIR="${HOME}/chatbot-backups/config"
DATE=$(date '+%Y%m%d_%H%M%S')

mkdir -p "${BACKUP_DIR}"

# 각 저장소의 설정 파일을 백업한다 (민감 정보가 없는 파일만 포함)
tar -czf "${BACKUP_DIR}/config_${DATE}.tar.gz" \
  --exclude='.env' \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='.git' \
  -C "${HOME}" \
  docker-compose.yml \
  docker-compose.prod.yml \
  .env.example \
  embedding-server/requirements.txt \
  backend/requirements.txt

echo "설정 백업 완료: ${BACKUP_DIR}/config_${DATE}.tar.gz"
