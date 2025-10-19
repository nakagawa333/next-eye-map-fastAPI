import os

import pytest


def pytest_configure():
    db_url_test = os.getenv("DATABASE_URL_TEST")
    if not db_url_test:
        raise RuntimeError("DATABASE_URL_TEST が設定されていません")

    #テストコード実行時にDBの環境変数を書き換え
    os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL_TEST")
