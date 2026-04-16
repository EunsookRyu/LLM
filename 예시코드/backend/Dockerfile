# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 의존성 파일을 먼저 복사하여 레이어 캐시를 활용한다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드를 복사한다.
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
