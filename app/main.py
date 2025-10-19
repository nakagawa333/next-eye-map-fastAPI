from contextlib import asynccontextmanager
from logging import getLogger

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware

from app.middleware.auth import AuthMiddleware
from app.routers import stores
from app.utils import translation
from config.logging_config import setup_logger

app =FastAPI(dependencies=[Depends(translation.get_locale)])

#バリデーションチェックエラーを日本語化
app.add_exception_handler(
    RequestValidationError, translation.validation_exception_handler
)

#cors設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(stores.router)

#ミドルウェア
app.add_middleware(AuthMiddleware)

#ログ設定
setup_logger()
        
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



