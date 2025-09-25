import traceback
from logging import getLogger

from fastapi import HTTPException, status
from httpx import AsyncClient, HTTPStatusError, RequestError

from app.config.constants import GSIAPI

logger = getLogger("app")


async def fetch_coordinates_from_gsi(params: dict):
    """
    国土地理院のAPIから緯度と経度を取得する

    Args:
        params (dict): パラメータ
    """
    async with AsyncClient() as client:
        logger.info(f"[GSI API] リクエスト開始 params={params}")
        try:
            # 国土地理院のAPIから緯度と経度を取得
            resp = await client.get(
                url=GSIAPI.ADDRESS_SEARCH, params=params, timeout=GSIAPI.TIMEOUT
            )
            resp.raise_for_status()
        except RequestError as e:
            logger.error(f"ネットワーク接続に失敗: \n{traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="国土地理院APIから応答がありません",
            )

        except HTTPStatusError as e:
            logger.error(f"HTTPステータスエラー: \n{traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="国土地理院APIから応答がありません",
            )

        except Exception as e:
            logger.error(f"サーバーエラー: \n{traceback.format_exc()}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="国土地理院APIへのリクエストが失敗しました",
            )
        logger.info(f"[GSI API] リクエスト終了 status={resp.status_code}")

    return resp
