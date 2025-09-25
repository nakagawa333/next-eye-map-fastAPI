from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from httpx import HTTPStatusError, Request, RequestError, Response

from app.config.constants import GSIAPI
from app.services.gsi_api import fetch_coordinates_from_gsi


@pytest.mark.asyncio
async def test_fetch_coordinates_from_gsi_success():
    """国土地理院APIからの座標取得成功テスト"""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(
        return_value=[{"geometry": {"coordinates": [139.7, 35.6]}}]
    )
    mock_response.raise_for_status = AsyncMock()
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.get.return_value = mock_response

    with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
        params = {"q": "Tokyo"}
        response = await fetch_coordinates_from_gsi(params)

        url = "https://msearch.gsi.go.jp/address-search/AddressSearch"
        timeout = 10
        mock_get.assert_awaited_once_with(
            url=url, params=params, timeout=timeout
        )

    mock_response.raise_for_status.assert_called_once()

    assert response.status_code == 200
    json_data = await response.json()
    assert json_data == [{"geometry": {"coordinates": [139.7, 35.6]}}]

@pytest.mark.asyncio
async def tets_fetch_coordinates_from_gsi_http_status_error():
    """国土地理院APIからの座標取得失敗テスト（HTTPエラー）"""
    mock_response = MagicMock()

    mock_response.raise_for_status.side_effect = HTTPStatusError(
        "Client Error 404",
        request=Request("GET", GSIAPI.ADDRESS_SEARCH),
        response=Response(
            status_code=404, request=Request("GET", GSIAPI.ADDRESS_SEARCH)
        ),
    )

    with patch(
        "httpx.AsyncClient.get",
        return_value=mock_response,
    ) as mock_get:
        params = {"q": "Tokyo"}

        # FastAPIのHTTPExceptionに変換されることを確認
        with pytest.raises(HTTPException) as exc:
            await fetch_coordinates_from_gsi(params)

        assert exc.value.detail == "国土地理院APIから応答がありません"
        assert exc.value.status_code == 400
    mock_response.raise_for_status.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_coordinates_from_gsi_request_error():
    """国土地理院APIからの座標取得失敗テスト（ネットワークエラー）"""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = RequestError(
        "Network error", request=Request("GET", GSIAPI.ADDRESS_SEARCH)
    )

    with patch(
        "httpx.AsyncClient.get",
        return_value=mock_response,
    ) as mock_get:
        params = {"q": "Tokyo"}

        # HTTPStatusError が送出されることを確認
        with pytest.raises(HTTPException) as exc:
            await fetch_coordinates_from_gsi(params)

        assert exc.value.detail == "国土地理院APIから応答がありません"
        assert exc.value.status_code == 400

        mock_response.raise_for_status.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_coordinates_from_gsi_error():
    """国土地理院APIからの座標取得失敗テスト"""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception

    with patch(
        "httpx.AsyncClient.get",
        return_value=mock_response
    ) as mock_get:
        params = {"q":"Tokyo"}

        # その他の例外が送出されることを確認        
        with pytest.raises(HTTPException) as exc:
            await fetch_coordinates_from_gsi(params)

        assert exc.value.detail == "国土地理院APIへのリクエストが失敗しました"
        assert exc.value.status_code == 500
    mock_response.raise_for_status.assert_called_once()





