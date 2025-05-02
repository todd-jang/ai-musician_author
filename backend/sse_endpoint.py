from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import time

router = APIRouter()

@router.get("/stream/logs")
async def stream_logs(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                print("🔌 연결 종료")
                break
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log = f"[{timestamp}] 실시간 로그 메시지"
            yield f"data: {log}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
