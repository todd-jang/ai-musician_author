from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import time

app = FastAPI()

# CORS 설정 (React와 연동 시 필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 또는 ["http://localhost:3000"] 등
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로그 스트리밍 SSE 엔드포인트
@app.get("/stream/logs")
async def stream_logs(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                print("클라이언트 연결 끊김")
                break
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_message = f"[{timestamp}] 새로운 로그 메시지입니다"
            yield f"data: {log_message}\n\n"
            await asyncio.sleep(1)  # 1초마다 전송

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# 예제 일반 API (프런트에서 추가 연동 가능)
@app.get("/status")
def status():
    return {"status": "running"}
