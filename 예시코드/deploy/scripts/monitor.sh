#!/bin/bash
# monitor.sh
# 크론탭에 등록하여 주기적으로 실행한다.

BACKEND_URL="http://localhost:8000"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL}"  # 선택 사항

response=$(curl -s -o /tmp/health_response.json -w "%{http_code}" "${BACKEND_URL}/health")
http_code=$response

if [ "$http_code" != "200" ]; then
    message="[내부 문서 AI 챗봇] 헬스체크 실패: HTTP ${http_code}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') | ERROR | ${message}" >> /var/log/chatbot-monitor.log

    # Slack 웹훅이 설정된 경우 알림을 전송한다.
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
          -H "Content-Type: application/json" \
          -d "{\"text\": \"${message}\"}"
    fi
else
    status=$(cat /tmp/health_response.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))")

    if [ "$status" != "healthy" ]; then
        services=$(cat /tmp/health_response.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('services', {}))")
        message="[내부 문서 AI 챗봇] 서비스 이상 감지: ${services}"
        echo "$(date '+%Y-%m-%d %H:%M:%S') | WARN | ${message}" >> /var/log/chatbot-monitor.log

        if [ -n "$SLACK_WEBHOOK_URL" ]; then
            curl -s -X POST "$SLACK_WEBHOOK_URL" \
              -H "Content-Type: application/json" \
              -d "{\"text\": \"${message}\"}"
        fi
    fi
fi
