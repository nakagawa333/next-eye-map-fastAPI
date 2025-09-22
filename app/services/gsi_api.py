from logging import getLogger
import httpx
from app.config.constants import GSIAPI

logger = getLogger("app")

async def fetch_coordinates_from_gsi(params:dict):
    """
    国土地理院のAPIから緯度と経度を取得する

    Args:
        params (dict): パラメータ
    """
    async with httpx.AsyncClient() as client:
        logger.info(f"[GSI API] リクエスト開始 params={params}")
        #国土地理院のAPIから緯度と経度を取得
        resp = await client.get(
            url=GSIAPI.ADDRESS_SEARCH, 
            params=params,
            timeout=GSIAPI.TIMEOUT
        )
        resp.raise_for_status()
        logger.info(f"[GSI API] リクエスト終了 status={resp.status_code}")

        return resp
