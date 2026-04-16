# main.py
# 가이드 참조: chapter8_document_indexing.md L799–L831
# Ch08 시점: documents 라우터 추가
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import chat, documents   # documents 추가

app = FastAPI(
    title="내부 문서 AI 챗봇 API",
    description="HyperCLOVA X 기반 내부 업무 RAG 챗봇 API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(documents.router)   # 추가


@app.get("/")
async def root():
    return {"status": "ok", "message": "내부 문서 AI 챗봇 API가 실행 중입니다."}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
