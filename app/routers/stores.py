from logging import getLogger
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from typing import List, Union

import humps
from app.config.constants import GSIAPI
from app.models.stores_tags_table import stores_tags_table
from sqlalchemy import func, insert, literal, select
from app.models.store import Store
from app.models.tag import Tag
from app.schemas.stores import StoreCreateRequest, StoreResponse, StoresResponse
from app.utils.db_exceptions import handle_db_exception
from database import Base, SessionLocal,engine
import httpx
import uuid
from fastapi import status
from config.logging_config import setup_logger
from uuid import UUID
import traceback

router = APIRouter(prefix="/stores",tags=["stores"])

logger = getLogger("app")

@router.get("/",response_model=StoresResponse)
def read_stores(serach_name: Union[str, None] = None):
    logger.info(f"店舗一覧取得リクエスト")

    with SessionLocal() as db:
        try:
            stmt = (
                select(
                    Store.store_id,
                    Store.store_name,
                    Store.address,
                    Store.content,
                    Store.lat,
                    Store.lng,
                    func.coalesce(
                        func.array_agg(Tag.tag_name).filter(Tag.tag_name != None),
                        literal([])
                    ).label("tags")
                )   
                .outerjoin(stores_tags_table, stores_tags_table.c.store_id == Store.id)
                .outerjoin(Tag, stores_tags_table.c.tag_id == Tag.id)
                .group_by(Store.id)
            )
            
            #検索文字あり   
            if serach_name:
                stmt = stmt.where(
                    Store.store_name.ilike(f"%{serach_name}%")
                )

            stores = db.execute(stmt).mappings().all()
        except Exception as e:
            logger.error(f"DB処理失敗: {e.__class__.__name__}: {e}")
            handle_db_exception(e)
        finally:
            logger.info("DB処理終了")
        
    return {
        "stores":humps.camelize(stores)
    }
    
@router.get("/{store_id}", response_model=StoreResponse)
def read_store(store_id: UUID):
    logger.info(f"店舗取得リクエスト: {store_id}")

    with SessionLocal() as db:
        logger.info("DB処理開始")
        try:
            stmt = (
                select(
                    Store.store_id,
                    Store.store_name,
                    Store.address,
                    Store.content,
                    Store.lat,
                    Store.lng,
                    func.coalesce(
                        func.array_agg(Tag.tag_name).filter(Tag.tag_name != None),
                        literal([])
                    ).label("tags")
                )   
                .outerjoin(stores_tags_table, stores_tags_table.c.store_id == Store.id)
                .outerjoin(Tag, stores_tags_table.c.tag_id == Tag.id)
                .where(Store.store_id == store_id)
                .group_by(Store.id)
            )
            store = db.execute(stmt).mappings().first()
        except Exception as e:
            logger.error(f"DB処理失敗: {e.__class__.__name__}: {e}")
            handle_db_exception(e)
        finally:
            logger.info("DB処理終了")
 
    if store is None:
        logger.warning(f"該当する店舗が存在しませんでした:{store_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="該当する店舗が存在しません")
        
    return humps.camelize(store)

@router.post("/")
async def create_store(store:StoreCreateRequest):
    logger.info(f"新規店舗作成リクエスト: {store.storeName}")
    
    params = {
        "q":store.address
    }

    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"国土地理院APIへのリクエスト開始: {store.storeName}")

            #国土地理院のAPIから緯度と経度を取得
            resp = await client.get(
                url=GSIAPI.ADDRESS_SEARCH, 
                params=params,
                timeout=GSIAPI.TIMEOUT
            )
            resp.raise_for_status()
            logger.info(f"国土地理院APIへのリクエスト終了 ステータス {resp.status_code}")

    except httpx.RequestError as e:
        logger.error(f"ネットワーク接続に失敗: \n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="国土地理院APIから応答がありません")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTPステータスエラー: \n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="国土地理院APIから応答がありません")
    
    except Exception as e:
        logger.error(f"サーバーエラー: \n{traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="国土地理院APIへのリクエストが失敗しました")

    if resp.status_code != status.HTTP_200_OK:
        logger.error("国土地理院APIから応答がありません")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="国土地理院APIから応答がありません")
    
    data = resp.json()

    if not data:
        logger.warning(f"該当する住所が存在しませんでした:{store.address}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="該当する住所が見つかりません")
    
    geometry = data[0].get("geometry")
    if not geometry or not geometry.get("coordinates"):
        logger.warning(f"該当する住所が存在しませんでした:{store.address}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="該当する住所が見つかりません")
    
    lng,lat = geometry.get("coordinates")

    with SessionLocal() as db:
        logger.info("トランザクション開始")

        try:
            #トランザクション開始
            with db.begin():
                select_tags:List[str] = []
                tag_stmt = (
                    select(
                        Tag.id,
                        Tag.tag_name
                    )
                    .where(Tag.tag_name.in_(store.tags))
                )

                #DB取得処理
                select_tags = db.execute(tag_stmt).mappings().all()
                
                set_select_tags = {select_tag.get("tag_name") for select_tag in select_tags}

                tag_ids:List[str] = []
                if store.tags:
                    tags_values:List[Tag] = []

                    for store_tag in store.tags:
                        #tagテーブルに存在しない場合、追加
                        if store_tag not in set_select_tags:
                            tag_id:uuid.UUID = uuid.uuid4()
                            tag:Tag = Tag(tag_id=tag_id,tag_name=store_tag)
                            tags_values.append(tag)

                    tags_dicts = [{"tag_id": t.tag_id, "tag_name": t.tag_name} for t in tags_values]
                    if tags_dicts:
                        logger.info(f"新規タグ追加: {[t['tag_name'] for t in tags_dicts]}")
                        insert_tag_stmt = insert(Tag).values(tags_dicts).returning(Tag.id)
                        tag_ids = db.execute(insert_tag_stmt).scalars().all()
                    else:
                        #既にテーブルにデータがある場合、IDのみを取得
                        tag_ids = [select_tag.get("id") for select_tag in select_tags]
                        logger.debug(f"既存タグ利用: {set_select_tags}")

                store_dicts = {
                    "store_id":uuid.uuid4(),
                    "store_name":store.storeName,
                    "address":store.address,
                    "content":store.content,
                    "lat":lat,
                    "lng":lng
                }

                store_id:str = None

                #店舗テーブルにデータを追加
                insert_store_stmt = insert(Store).values(store_dicts).returning(Store.id)
                store_id = db.execute(insert_store_stmt).scalar_one()

                logger.info(f"店舗登録成功: store_id={store_id}, name={store.storeName}")
                
                #中間テーブルにデータを追加
                if tag_ids:
                    stores_tags = []
                    for tag_id in tag_ids:
                        stores_tags_dicts = {
                            "stores_tags_id":uuid.uuid4(),
                            "store_id":store_id,
                            "tag_id":tag_id                    
                        }
                        stores_tags.append(stores_tags_dicts)

                    logger.debug(f"中間テーブル登録データ: {stores_tags}")
                    insert_stores_tags_stmt = insert(stores_tags_table).values(stores_tags)
                    db.execute(insert_stores_tags_stmt)
                    
        except Exception as e:
            logger.error("トランザクション失敗")
            handle_db_exception(e)
        logger.info("トランザクション終了")

    return Response(status_code=status.HTTP_201_CREATED)
