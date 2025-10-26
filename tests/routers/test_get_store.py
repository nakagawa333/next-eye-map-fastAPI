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
            },
            {
                "store_id": "33333333-3333-3333-3333-333333333333",
                "store_name": "store3",
                "address": "住所3",
                "content": "内容3",
                "lat": 10,
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


@pytest.mark.parametrize(
    "store_id,store_name,address,content,lat,lng,tags",
    [
        pytest.param("11111111-1111-1111-1111-111111111111","store1", "住所1","内容1",30.0,25.0,["タグ1"],id="正常系 タグ取得"),
        pytest.param("33333333-3333-3333-3333-333333333333","store3", "住所3","内容3",10.0,15.0,[],id="正常系 タグなし")
    ]
)
def test_success(store_id,store_name,address,content,lat,lng,tags,test_setup,sample_stores):
    path = f"/stores/{store_id}"

    #期待値
    expected_response = {
        "storeId": store_id,
        "storeName": store_name,
        "address": address,
        "content": content,
        "lat": lat,
        "lng": lng,
        "tags":tags
    }
    
    with TestClient(app) as client:
        response = client.get(path)
        response_json = response.json()

    assert response.status_code == 200
    assert response_json == expected_response

@pytest.mark.parametrize(
    "store_id",
    [
        pytest.param("11111112-1111-1111-1111-111111111111",id="正常系 タグ取得")
    ]
)
def test_data_none(store_id,test_setup,sample_stores):
    path = f"/stores/{store_id}"
    with TestClient(app) as client:
        response = client.get(path)
        response_json = response.json()

    assert response.status_code == 404
    assert response_json == {"detail":"該当する店舗が存在しませんでした"}

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
    "store_id,exc_class,kwargs,status_code,detail",
    [
        pytest.param("11111111-1111-1111-1111-111111111111",OperationalError,{"statement":"SELECT 1","params":None,"orig":Exception("DB接続失敗")},503,"データベースに接続できません",id="OperationalError"),
        pytest.param("11111111-1111-1111-1111-111111111111",IntegrityError,{"statement":"INSERT INTO ...","params":None,"orig":Exception("データ整合性の問題")},400,"データ整合性の問題が発生しました",id="IntegrityError"),
        pytest.param("11111111-1111-1111-1111-111111111111",HTTPException,{"status_code":404,"detail":"データ整合性に失敗","headers":None},404,"データ整合性に失敗",id="HTTPException"),
    ]
)
def test_db_exceptions(store_id,exc_class,kwargs,status_code,detail,test_setup,mock_db_exception):
    mock_db_exception(exc_class,**kwargs)
    with TestClient(app) as client:
        response = client.get(f"/stores/{store_id}")
        assert response.status_code == status_code
        assert response.json() == {"detail":detail}

@pytest.mark.parametrize(
    "store_id",
    [
        pytest.param("11111111-1111-1111-1111-111111111111",id="Exception"),
    ]
)
def test_db_error(store_id,test_setup,clean_app_dependency):
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
        response = client.get(f"/stores/{store_id}")

    assert response.status_code == 500

    expected_response = {
        "detail":"サーバーエラーが発生しました"
    }

    assert response.json() == expected_response

@pytest.mark.parametrize(
    "store_id,expected_port",
    [
        pytest.param("1111111-1111-1111-1111-111111111111",404,id="バリデーションチェックエラー UUID桁数不足"),
        pytest.param("111111111-1111-1111-1111-111111111111",404,id="バリデーションチェックエラー UUID桁数超過"),
        pytest.param(" ",404,id="バリデーションチェックエラー スペース"),
        pytest.param(None,404,id="バリデーションチェックエラー None")
    ],
)
def test_validation(store_id, expected_port, test_setup):
    """
    バリデーションチェックのテスト

    Args:
        obj (_type_): _description_
        test_setup (_type_): _description_
    """
    path = f"/stores/{store_id}"

    with TestClient(app) as client:
        response = client.get(path)

    assert response.status_code == expected_port