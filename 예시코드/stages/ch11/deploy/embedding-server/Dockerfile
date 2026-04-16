# embedding-server/Dockerfile
# 가이드 참조: chapter11_embedding_server.md L495–L510
FROM python:3.11-slim

WORKDIR /app

# torch는 크기가 크므로 먼저 설치하여 캐싱 효과를 높인다.
RUN pip install --no-cache-dir torch==2.3.1 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
