from logging import getLogger
from sqlalchemy.exc import IntegrityError, OperationalError
import traceback
from fastapi import HTTPException, status

logger = getLogger("app")

def handle_db_exception(exc):
    """DB例外の共通処理"""

    if isinstance(exc, OperationalError):
        logger.error(f"データベース接続失敗:\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="データベースに接続できません")
    elif isinstance(exc, IntegrityError):
        logger.error(f"データ整合性の問題:\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="データ整合性の問題が発生しました")
    elif isinstance(exc, HTTPException):
        logger.error(f"データ未存在:\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.detail)
    else:
        logger.error(f"サーバーエラー:\n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="サーバーエラーが発生しました")