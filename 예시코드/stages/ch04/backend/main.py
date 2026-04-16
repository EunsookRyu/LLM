# main.py
# 가이드 참조: chapter4_hyperclovax.md L603–L640
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat

app = FastAPI(
    title="내부 문서 AI 챗봇 API",
    description="HyperCLOVA X 기반 챗봇 API. 이후 로컬 LLM으로 교체 가능.",
    version="1.0.0",
)

# CORS 설정
# 프론트엔드(Streamlit, NextChat 등)에서의 API 요청을 허용한다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",    # Streamlit 개발 서버
        "http://localhost:3000",    # NextChat 개발 서버
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(chat.router)


@app.get("/")
async def root():
    return {"status": "ok", "message": "내부 문서 AI 챗봇 API가 실행 중입니다."}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
