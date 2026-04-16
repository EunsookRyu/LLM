# main.py
# 가이드 참조: chapter3_python.md L419–L446
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="내부 문서 AI 챗봇 API",
    description="HyperCLOVA X 기반 챗봇 API",
    version="0.1.0"
)

# Streamlit(포트 8501) 또는 NextChat(포트 3000)에서의 요청을 허용하기 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
