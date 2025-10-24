import os
import uuid
from unittest.mock import MagicMock

import pytest
import requests
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.testclient import TestClient
from pytest_postgresql import factories
from sqlalchemy import create_engine, delete, insert
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.main import app
from app.models.store import Store
from app.models.stores_tags_table import stores_tags_table
from app.models.tag import Tag
from database import get_db, get_session_local

postgresql_noproc = factories.postgresql_noproc()
postgresql_fixture = factories.postgresql(
    "postgresql_noproc",
)


@pytest.fixture()
def test_setup():
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        #db初期化
        db_init(db)
        yield db

    finally:
        #db初期化
        db_init(db)
        db.close()

def db_init(db:Session):
    """
    DB初期化

    Args:
        db (Session): dbセッション
    """
    delete_stores_tags_table_stmt = delete(stores_tags_table)
    delete_tag_stmt = delete(Tag)
    delete_store_stmt = delete(Store)

    db.execute(delete_stores_tags_table_stmt)
    db.execute(delete_tag_stmt)
    db.execute(delete_store_stmt)
    db.commit()

# 3. データ準備用 fixture
@pytest.fixture
def sample_stores():

    SessionLocal = get_session_local()
    with SessionLocal() as db:
        store_datas = [
            {
                "store_id": "11111111-1111-1111-1111-111111111111",
                "store_name": "store1",
                "address": "住所1",
                "content": "内容1",
                "lat": 30,
                "lng": 25
            },
            {
                "store_id": "22222222-2222-2222-2222-222222222222",
                "store_name": "store2",
                "address": "住所2",
                "content": "内容2",
                "lat": 20,
                "lng": 15
            }
        ]

        # 店舗テーブルにデータを追加
        insert_store_stmt = (
            insert(Store).values(store_datas).returning(Store.id)
        )

        insert_store_result = db.execute(insert_store_stmt)
        insert_store_rows = insert_store_result.mappings().all()
        store_ids = [r.id for r in insert_store_rows]

        tag_datas = [
            {
                "tag_id":"aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "tag_name":"タグ1"
            },
            {
                "tag_id":"bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
                "tag_name":"タグ2"
            }
        ]

        #タグテーブルにデータを追加
        insert_tags_stmt = (
            insert(Tag).values(tag_datas).returning(Tag.id)
        )

        insert_tags_result = db.execute(insert_tags_stmt)
        insert_tags_rows = insert_tags_result.mappings().all()

        tag_ids = [r.id for r in insert_tags_rows]

        stores_tags_datas = []
        stores_tags_dict1 = {
            "stores_tags_id": "aaaaaaaa-1111-1111-1111-aaaaaaaaaaaa",
            "store_id": store_ids[0],
            "tag_id": tag_ids[0],
        }

        stores_tags_dict2 = {
            "stores_tags_id": "aaaaaaaa-2222-2222-2222-aaaaaaaaaaaa",
            "store_id": store_ids[1],
            "tag_id": tag_ids[1],
        }
        
        stores_tags_datas.append(stores_tags_dict1)
        stores_tags_datas.append(stores_tags_dict2)

        insert_stores_tags_stmt = (
            insert(stores_tags_table).values(stores_tags_datas)
        )

        db.execute(insert_stores_tags_stmt)
        db.commit()

@pytest.fixture(autouse=True)
def clean_app_dependency():
    # テスト前
    yield
    # テスト後（リセット）
    app.dependency_overrides.clear()

@pytest.mark.asyncio
def test_success(test_setup,sample_stores):
    path = "/stores"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    #期待値
    expected_response = {
        "stores": [
            {
                "storeId": "11111111-1111-1111-1111-111111111111",
                "storeName": "store1",
                "address": "住所1",
                "content": "内容1",
                "lat": 30.0,
                "lng": 25.0,
                "tags":["タグ1"]
            },
            {
                "storeId": "22222222-2222-2222-2222-222222222222",
                "storeName": "store2",
                "address": "住所2",
                "content": "内容2",
                "lat": 20.0,
                "lng": 15.0,
                "tags":["タグ2"]
            }
        ]
    }

    with TestClient(app) as client:
        response = client.get(path, headers=headers)
        response_json = response.json()

    assert response.status_code == 200
    assert response_json == expected_response

@pytest.mark.parametrize(
    "key,value",
    [
        pytest.param("serach_name", "store1", id="正常系")
    ]
)
def test_success_search_name_filter(key,value,test_setup,sample_stores):
    path = f"/stores?{key}={value}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    #期待値
    expected_response = {
        "stores": [
            {
                "storeId": "11111111-1111-1111-1111-111111111111",
                "storeName": "store1",
                "address": "住所1",
                "content": "内容1",
                "lat": 30.0,
                "lng": 25.0,
                "tags":["タグ1"]
            }
        ]
    }

    with TestClient(app) as client:
        response = client.get(path, headers=headers)
        response_json = response.json()

    assert response.status_code == 200
    assert response_json == expected_response

@pytest.mark.parametrize(
    "key,value",
    [
        pytest.param("tag_name", "タグ2", id="正常系")
    ]
)
def test_success_tag_name_filter(key,value,test_setup,sample_stores):
    path = f"/stores?{key}={value}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    #期待値
    expected_response = {
        "stores": [
            {
                "storeId": "22222222-2222-2222-2222-222222222222",
                "storeName": "store2",
                "address": "住所2",
                "content": "内容2",
                "lat": 20.0,
                "lng": 15.0,
                "tags":["タグ2"]
            }
        ]
    }

    with TestClient(app) as client:
        response = client.get(path, headers=headers)
        response_json = response.json()

    assert response.status_code == 200
    assert response_json == expected_response

@pytest.fixture
def mock_db_exception():
    def _mock(exc_class,**kwarges):
        mock_db = MagicMock()
        mock_db.execute.side_effect = exc_class(**kwarges)

        class MockSession:
            def execute(self,*args,**kwargs):
                return mock_db.execute(*args,**kwargs)
            
        app.dependency_overrides[get_db] = lambda: MockSession()
        return MockSession
    return _mock

@pytest.mark.parametrize(
    "exc_class,kwargs,status_code,detail",
    [
        pytest.param(OperationalError,{"statement":"SELECT 1","params":None,"orig":Exception("DB接続失敗")},503,"データベースに接続できません",id="OperationalError"),
        pytest.param(IntegrityError,{"statement":"INSERT INTO ...","params":None,"orig":Exception("データ整合性の問題")},400,"データ整合性の問題が発生しました",id="IntegrityError"),
        pytest.param(HTTPException,{"status_code":404,"detail":"データ整合性に失敗","headers":None},404,"データ整合性に失敗",id="HTTPException"),
    ]
)
def test_db_exceptions(exc_class,kwargs,status_code,detail,test_setup,mock_db_exception):
    mock_db_exception(exc_class,**kwargs)
    with TestClient(app) as client:
        response = client.get("/stores")
        assert response.status_code == status_code
        assert response.json() == {"detail":detail}

def test_db_error(test_setup,clean_app_dependency):
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("例外が発生")

    def mock_execute(*args, **kwargs):
        operational_error = mock_db.execute.side_effect = Exception("例外が発生")
        raise operational_error

    # --- ② FastAPIの依存関係 get_db をモック ---
    class MockSession:
        def execute(self, *args, **kwargs):
            return mock_execute()

    def override_get_db():
        yield MockSession()

    app.dependency_overrides = { }
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        response = client.get("/stores")

    assert response.status_code == 500

    expected_response = {
        "detail":"サーバーエラーが発生しました"
    }

    assert response.json() == expected_response

@pytest.mark.parametrize(
    "serach_name,tag_name,expected_port",
    [
        pytest.param("", "", 200, id="正常系 値が空文字"),
        pytest.param(None,  None, 200, id="正常系 値がNone"),
        pytest.param("s" * 99, "t" * 99, 200, id="search_name 99文字: 境界値テスト"),
        pytest.param("s" * 100, "t" * 99, 200, id="search_name 100文字: 上限境界値"),
        pytest.param(
            "s" * 101, "t" * 101, 404, id="search_name 101文字: 上限超過境界値"
        ),
    ],
)
def test_validation(serach_name, tag_name, expected_port, test_setup):
    """
    バリデーションチェックのテスト

    Args:
        obj (_type_): _description_
        test_setup (_type_): _description_
    """
    path = f"/stores?serach_name={serach_name}&tag_name={tag_name}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}

    with TestClient(app) as client:
        response = client.get(path, headers=headers)

    assert response.status_code == expected_port
