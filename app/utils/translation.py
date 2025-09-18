from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic_i18n import PydanticI18n
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY
from fastapi import status

__all__  = ["get_locale","validation_exception_handler"]

DEFAULT_LOCALE = "ja_JP"

translations = {
    "en_US": {
        "field required": "",
        "value is not a valid integer": "",
        "ensure this value has at least {} characters": "",
        "ensure this value has at most {} characters": "",
        "ensure this value is less than or equal to {}": "",
        "ensure this value is less than {}": "",
        "ensure this value is greater than or equal to {}": "",
        "none is not an allowed value":"",
        "value is not a valid list":""
    },
    "ja_JP": {
        "field required": "必須入力です。",
        "value is not a valid integer": "半角数字で入力してください。",
        "ensure this value has at least {} characters": "{}文字以上で入力してください。",
        "ensure this value has at most {} characters": "{}文字以下で入力してください。",
        "ensure this value is less than {}": "{}未満で入力してください。",
        "ensure this value is less than or equal to {}": "{}以下で入力してください。",
        "ensure this value is greater than or equal to {}": "{}以上で入力してください。",
        "none is not an allowed value":"nullは許可されていません",
        "value is not a valid list":"リスト形式で入力してください"
    },
}

tr = PydanticI18n(translations)

def get_locale(locale:str = DEFAULT_LOCALE):
    return locale

async def validation_exception_handler(request:Request,exc:RequestValidationError):
    """
    バリデーションエラー発生時に呼び出される例外ハンドラ。
    エラーメッセージを指定されたロケールに翻訳し、JSON レスポンスとして返す。

    Args:
        request (Request): FastAPI のリクエストオブジェクト。
        クエリパラメータから "locale" を取得して使用する。
        exc (RequestValidationError): Pydantic のバリデーションエラー情報。

    Returns:
        JSONResponse: 翻訳済みのエラーメッセージを含む JSON レスポンス。
        ステータスコードは 404。
    """

    current_locale = request.query_params.get("locale",DEFAULT_LOCALE)

    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": tr.translate(exc.errors(), current_locale)},
    )