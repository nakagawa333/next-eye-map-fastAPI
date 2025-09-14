from typing import Final
#定数クラス

class GSIAPI:
    BASE_URL:Final[str] = "https://msearch.gsi.go.jp"
    ADDRESS_SEARCH: Final[str] = f"{BASE_URL}/address-search/AddressSearch"
    TIMEOUT: Final[str] = 10

class EndPoints:
    STORES:Final[str] = "/stores"

class HttpMethod:
    GET:Final[str] = "GET"
    POST:Final[str] = "POST"
    PUT:Final[str] = "PUT"
    PATCH:Final[str] = "PATCH"
    DELETE:Final[str] = "DELETE"
