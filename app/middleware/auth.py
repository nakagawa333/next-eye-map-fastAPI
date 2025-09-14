import logging
import os
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from app.config.constants import EndPoints, HttpMethod
from fastapi import status

logger = logging.getLogger("app")
EXPECTED_TOKEN = os.getenv("API_TOKEN")

#ミドルウェア
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self,request:Request,call_next):
        if request.url.path.startswith(EndPoints.STORES) and request.method == HttpMethod.POST:
            logger.info(f"認証開始: path={request.url.path}, method={request.method}, client={request.client.host}")
            #Authorizationヘッダー取得
            token:str = request.headers.get("Authorization")

            if not token:
                logger.warning(f"Authorizationヘッダーが存在しません: path={request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authorizationヘッダーが存在しません"}
                )
            
            if token != f"Bearer {EXPECTED_TOKEN}":
                logger.warning(f"無効なAuthorizationヘッダー: {token[:6]}, path={request.url.path}")
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Authorizationヘッダーの値が無効です"}
                )
            
            logger.info(f"認証成功: path={request.url.path}, method={request.method}")

        response = await call_next(request)
        return response
        
