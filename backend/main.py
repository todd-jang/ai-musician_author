from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_endpoint import router as sse_router

app = FastAPI()

# CORS 설정 (React 클라이언트 연동용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중은 전체 허용, 운영은 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSE 엔드포인트 라우터 등록
app.include_router(sse_router)

@app.get("/status")
def read_root():
    return {"message": "FastAPI 서버 정상 동작 중!"}
