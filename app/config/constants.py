from typing import Final
#定数クラス

class GSIAPI:
    BASE_URL:Final[str] = "https://msearch.gsi.go.jp"
    ADDRESS_SEARCH: Final[str] = f"{BASE_URL}/address-search/AddressSearch"
    TIMEOUT: Final[str] = 10