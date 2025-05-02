## backend/app/main.py

#from fastapi import FastAPI

## FastAPI 애플리케이션 인스턴스 생성
## 기본적인 라우트 정의 (선택 사항이지만 앱이 잘 작동하는지 확인하기 좋음)
#@app.get("/")
#def read_root():
#    return {"message": "Personal Data Assistant Backend is running!"}

# 나중에 API 라우터를 포함시킬 부분
# from .api import api_router
# app.include_router(api_router)

# 이 파일을 직접 실행하려면:
# uvicorn app.main:app --reload
# (FastAPI 및 uvicorn 설치 필요: pip install fastapi uvicorn python-multipart boto3)


# backend/app/main.py

from fastapi import FastAPI

# 파일 API 라우터 임포트
from .api import files # api 디렉토리의 files.py 모듈을 임포트

# FastAPI 애플리케이션 인스턴스 생성
app = FastAPI()

# 기본적인 라우트 정의
@app.get("/")
def read_root():
    return {"message": "Personal Data Assistant Backend is running!"}

# 파일 API 라우터를 메인 애플리케이션에 포함
# prefix를 설정하면 해당 라우터의 모든 경로는 /files로 시작하게 됩니다.
# 예: /files/uploadfile/, /files/uploadfiles/
app.include_router(files.router, prefix="/files", tags=["files"])

# 이 파일을 직접 실행하려면:
# uvicorn app.main:app --reload
